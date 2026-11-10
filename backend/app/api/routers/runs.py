import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionDep
from app.models import Dataset, ModelConfig, PromptVersion, Result, Run
from app.schemas import RunCreate, RunDetail, RunOut

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=201)
async def create_run(body: RunCreate, request: Request, session: SessionDep):
    dataset = await session.get(Dataset, body.dataset_id)
    prompt = await session.get(PromptVersion, body.prompt_version_id)
    config = await session.get(ModelConfig, body.model_config_id)
    if not (dataset and prompt and config):
        raise HTTPException(404, "dataset, prompt version or model config not found")

    run = Run(
        dataset_id=dataset.id,
        prompt_version_id=prompt.id,
        model_config_id=config.id,
        prompt_snapshot=prompt.template,
        model_snapshot={
            "provider": config.provider,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        },
        git_sha=body.git_sha,
    )
    session.add(run)
    await session.commit()
    # The API only enqueues; the worker does the (slow) LLM calls.
    await request.app.state.arq.enqueue_job("run_eval", str(run.id))
    return run


@router.get("", response_model=list[RunOut])
async def list_runs(session: SessionDep):
    return (await session.scalars(select(Run).order_by(Run.created_at.desc()).limit(50))).all()


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: uuid.UUID, session: SessionDep):
    run = await session.scalar(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.results).selectinload(Result.scores),
            selectinload(Run.results).selectinload(Result.test_case),
        )
    )
    if run is None:
        raise HTTPException(404, "run not found")
    return run
