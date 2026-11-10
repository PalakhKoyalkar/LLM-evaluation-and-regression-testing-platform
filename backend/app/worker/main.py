import asyncio
import uuid
from datetime import datetime, timezone

from arq.connections import RedisSettings
from sqlalchemy import func, select, update

from app.config import settings
from app.db import SessionLocal
from app.models import Result, Run, Score, TestCase
from app.worker.providers import Provider, get_provider
from app.worker.scorers import exact_match
from app.worker.templating import render


async def evaluate_case(sem: asyncio.Semaphore, provider: Provider, run: Run, case: TestCase) -> None:
    result = Result(run_id=run.id, test_case_id=case.id)
    async with sem:
        try:
            prompt = render(run.prompt_snapshot, case.input)
            completion = await provider.complete(prompt, run.model_snapshot)
            result.output = completion.text
            result.latency_ms = completion.latency_ms
            result.input_tokens = completion.input_tokens
            result.output_tokens = completion.output_tokens
            result.cost_usd = completion.cost_usd
            score = exact_match(completion.text, case.expected_output)
            if score is not None:
                result.scores.append(score)
        except Exception as e:
            # One bad case must not kill the whole run.
            result.error = f"{type(e).__name__}: {e}"

    async with SessionLocal() as session:
        session.add(result)
        await session.execute(
            update(Run).where(Run.id == run.id).values(completed_cases=Run.completed_cases + 1)
        )
        await session.commit()


async def finish_run(run_id: uuid.UUID, **values) -> None:
    async with SessionLocal() as session:
        await session.execute(
            update(Run).where(Run.id == run_id).values(finished_at=datetime.now(timezone.utc), **values)
        )
        await session.commit()


async def run_eval(ctx, run_id: str) -> None:
    rid = uuid.UUID(run_id)
    async with SessionLocal() as session:
        run = await session.get(Run, rid)
        if run is None:
            return
        cases = (await session.scalars(select(TestCase).where(TestCase.dataset_id == run.dataset_id))).all()
        run.status = "running"
        run.total_cases = len(cases)
        await session.commit()

    try:
        provider = get_provider(run.model_snapshot["provider"])
        sem = asyncio.Semaphore(settings.worker_concurrency)
        await asyncio.gather(*(evaluate_case(sem, provider, run, c) for c in cases))

        # Aggregate in SQL rather than from the detached Result objects.
        async with SessionLocal() as session:
            avg_score = await session.scalar(
                select(func.avg(Score.value)).join(Result).where(Result.run_id == rid)
            )
            total_cost, errors = (
                await session.execute(
                    select(func.coalesce(func.sum(Result.cost_usd), 0.0), func.count(Result.error))
                    .where(Result.run_id == rid)
                )
            ).one()
    except Exception as e:
        await finish_run(rid, status="failed", error=f"{type(e).__name__}: {e}")
        raise

    await finish_run(
        rid,
        status="failed" if cases and errors == len(cases) else "completed",
        avg_score=avg_score,
        total_cost_usd=total_cost,
        error_count=errors,
    )


class WorkerSettings:
    functions = [run_eval]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 3600
