import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    # protected_namespaces=() allows field names like model_config_id / model_snapshot.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TestCaseIn(Schema):
    input: dict[str, Any]
    expected_output: str | None = None
    tags: list[str] = []


class TestCaseOut(TestCaseIn):
    id: uuid.UUID


class DatasetOut(Schema):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    case_count: int


class PromptCreate(Schema):
    name: str
    template: str


class PromptOut(PromptCreate):
    id: uuid.UUID
    version: int
    created_at: datetime


class ModelConfigCreate(Schema):
    provider: Literal["openai", "mock"]
    model: str
    temperature: float = 0.0
    max_tokens: int = 512


class ModelConfigOut(ModelConfigCreate):
    id: uuid.UUID


class RunCreate(Schema):
    dataset_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_config_id: uuid.UUID
    git_sha: str | None = None


class ScoreOut(Schema):
    scorer: str
    value: float
    reasoning: str | None


class ResultOut(Schema):
    id: uuid.UUID
    test_case: TestCaseOut
    output: str | None
    latency_ms: int | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None
    scores: list[ScoreOut]


class RunOut(Schema):
    id: uuid.UUID
    dataset_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_config_id: uuid.UUID
    status: str
    total_cases: int
    completed_cases: int
    error_count: int
    avg_score: float | None
    total_cost_usd: float
    created_at: datetime
    finished_at: datetime | None


class RunDetail(RunOut):
    results: list[ResultOut]
