from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.api.routers import datasets, model_configs, prompts, runs
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq.aclose()


app = FastAPI(title="LLM Eval Platform", lifespan=lifespan)

for module in (datasets, prompts, model_configs, runs):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"ok": True}
