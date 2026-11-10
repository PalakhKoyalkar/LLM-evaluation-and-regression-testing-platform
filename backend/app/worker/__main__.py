from arq import run_worker

from app.worker.main import WorkerSettings

run_worker(WorkerSettings)
