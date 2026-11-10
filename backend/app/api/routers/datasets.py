from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionDep
from app.models import Dataset, TestCase
from app.schemas import DatasetOut, TestCaseIn

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    session: SessionDep,
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(..., description="JSONL: one test case per line"),
):
    try:
        text = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "file must be UTF-8 encoded")

    cases = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = TestCaseIn.model_validate_json(line)
        except ValidationError as e:
            raise HTTPException(422, f"line {lineno}: {e.errors()[0]['msg']}")
        cases.append(TestCase(**row.model_dump()))
    if not cases:
        raise HTTPException(422, "dataset is empty")

    dataset = Dataset(name=name, description=description, test_cases=cases)
    session.add(dataset)
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(409, f"dataset '{name}' already exists")
    return DatasetOut(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        created_at=dataset.created_at,
        case_count=len(cases),
    )


@router.get("", response_model=list[DatasetOut])
async def list_datasets(session: SessionDep):
    rows = await session.execute(
        select(Dataset, func.count(TestCase.id))
        .outerjoin(TestCase)
        .group_by(Dataset.id)
        .order_by(Dataset.created_at.desc())
    )
    return [
        DatasetOut(id=d.id, name=d.name, description=d.description, created_at=d.created_at, case_count=n)
        for d, n in rows
    ]
