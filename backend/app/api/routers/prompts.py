from fastapi import APIRouter
from sqlalchemy import func, select

from app.db import SessionDep
from app.models import PromptVersion
from app.schemas import PromptCreate, PromptOut

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut, status_code=201)
async def create_prompt(body: PromptCreate, session: SessionDep):
    # Saving under an existing name creates the next version.
    latest = await session.scalar(
        select(func.max(PromptVersion.version)).where(PromptVersion.name == body.name)
    )
    prompt = PromptVersion(name=body.name, template=body.template, version=(latest or 0) + 1)
    session.add(prompt)
    await session.commit()
    return prompt


@router.get("", response_model=list[PromptOut])
async def list_prompts(session: SessionDep):
    stmt = select(PromptVersion).order_by(PromptVersion.name, PromptVersion.version.desc())
    return (await session.scalars(stmt)).all()
