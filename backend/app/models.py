import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Defaults are Python-side (default=) rather than server_default= so values are populated on
# flush; reading a server-generated column after commit would trigger a lazy load, which fails
# under async SQLAlchemy.


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    test_cases: Mapped[list["TestCase"]] = relationship(cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # not a pytest test class
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB)
    expected_output: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int]
    template: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelConfig(Base):
    __tablename__ = "model_configs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    temperature: Mapped[float] = mapped_column(default=0.0)
    max_tokens: Mapped[int] = mapped_column(default=512)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"))
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prompt_versions.id"))
    model_config_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_configs.id"))
    # Snapshots make a run reproducible even if the prompt/config rows change later.
    prompt_snapshot: Mapped[str] = mapped_column(Text)
    model_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    git_sha: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    total_cases: Mapped[int] = mapped_column(default=0)
    completed_cases: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    avg_score: Mapped[float | None]
    total_cost_usd: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    results: Mapped[list["Result"]] = relationship(cascade="all, delete-orphan")


class Result(Base):
    __tablename__ = "results"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"))
    output: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None]
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    error: Mapped[str | None] = mapped_column(Text)
    test_case: Mapped[TestCase] = relationship()
    scores: Mapped[list["Score"]] = relationship(cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("results.id", ondelete="CASCADE"), index=True)
    scorer: Mapped[str] = mapped_column(String(50))
    value: Mapped[float]  # normalized 0..1
    reasoning: Mapped[str | None] = mapped_column(Text)
