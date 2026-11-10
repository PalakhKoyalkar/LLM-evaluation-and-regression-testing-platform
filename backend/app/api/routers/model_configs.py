from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models import ModelConfig
from app.schemas import ModelConfigCreate, ModelConfigOut

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


@router.post("", response_model=ModelConfigOut, status_code=201)
async def create_model_config(body: ModelConfigCreate, session: SessionDep):
    config = ModelConfig(**body.model_dump())
    session.add(config)
    await session.commit()
    return config


@router.get("", response_model=list[ModelConfigOut])
async def list_model_configs(session: SessionDep):
    return (await session.scalars(select(ModelConfig).order_by(ModelConfig.created_at.desc()))).all()
