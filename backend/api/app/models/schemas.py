"""Pydantic schemas for API request/response bodies."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.db_models import (
    AgentModel,
    DriftSeverity,
    DriftSignalType,
    ExtractorHealth,
    ExtractorStatus,
    RepairStrategy,
    RunStatus,
    RunTrigger,
)


class CreateExtractorRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
        description="Human-readable name for this extractor",
        examples=["Product Prices"],
    )
    urls: list[str] = Field(
        min_length=1,
        description="URLs to extract data from",
        examples=[["https://example.com/product"]],
    )
    prompt: str = Field(
        min_length=1,
        description="Natural-language instructions for what data to extract",
        examples=["Extract the product name, price, currency, and availability status"],
    )
    schema_definition: dict[str, Any] = Field(
        description="JSON Schema describing the expected structured output",
    )
    schedule: str | None = Field(
        default=None,
        description='Optional schedule for future monitor/cron (e.g. "every 6 hours")',
    )
    model: AgentModel = Field(
        default=AgentModel.SPARK_1_MINI,
        description="Firecrawl agent model tier to use for extractions",
    )


class UpdateExtractorRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    urls: list[str] | None = Field(default=None, min_length=1)
    prompt: str | None = Field(default=None, min_length=1)
    schema_definition: dict[str, Any] | None = None
    schedule: str | None = None
    status: ExtractorStatus | None = None
    model: AgentModel | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UpdateExtractorRequest":
        if all(
            value is None
            for value in (
                self.name,
                self.urls,
                self.prompt,
                self.schema_definition,
                self.schedule,
                self.status,
                self.model,
            )
        ):
            raise ValueError("At least one field must be provided")
        return self


class DriftSignalOut(BaseModel):
    id: str
    run_id: str
    field: str
    signal_type: DriftSignalType
    expected: str
    actual: str
    severity: DriftSeverity


class RepairAttemptOut(BaseModel):
    id: str
    run_id: str
    strategy: RepairStrategy
    succeeded: bool
    prompt_used: str | None = None
    model_used: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int
    credits_used: int


class ExtractorResponse(BaseModel):
    id: str = Field(description="UUID primary key")
    name: str
    urls: list[str]
    prompt: str
    schema_definition: dict[str, Any]
    schedule: str | None = None
    monitor_id: str | None = Field(
        default=None,
        description="Linked Firecrawl monitor ID (set when monitor integration is added)",
    )
    status: ExtractorStatus = Field(description="Operational status")
    health: ExtractorHealth = Field(description="Health based on recent run quality")
    model_preference: AgentModel
    consecutive_failures: int = Field(description="Consecutive failed runs")
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent extraction run",
    )
    run_count: int = Field(default=0, description="Total extraction runs")
    success_rate: float = Field(default=0.0, description="Fraction of successful runs (0–1)")


class RunResponse(BaseModel):
    id: str
    extractor_id: str
    status: RunStatus
    trigger: RunTrigger
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    data: dict[str, Any] | None = None
    validation_errors: list[str] = Field(default_factory=list)
    drift_signals: list[DriftSignalOut] = Field(default_factory=list)
    repair_attempts: list[RepairAttemptOut] = Field(default_factory=list)
    was_repaired: bool = False
    credits_used: int = 0
    error: str | None = None


class FleetHealthResponse(BaseModel):
    total_extractors: int
    healthy: int
    warning: int
    critical: int
    runs_today: int = 0
    repairs_today: int = 0
    failures_today: int = 0
    credits_used_today: int = 0
    extractors_needing_attention: list[str] = Field(default_factory=list)
