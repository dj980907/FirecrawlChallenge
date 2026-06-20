"""Pydantic schemas for API request/response bodies."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

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
    name: str = Field(min_length=1, max_length=200)
    urls: list[str] = Field(min_length=1)
    prompt: str = Field(min_length=1)
    schema_definition: dict[str, Any]
    schedule: str | None = None
    model: AgentModel = AgentModel.SPARK_1_MINI


class UpdateExtractorRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    urls: list[str] | None = Field(default=None, min_length=1)
    prompt: str | None = Field(default=None, min_length=1)
    schema_definition: dict[str, Any] | None = None
    schedule: str | None = None
    status: ExtractorStatus | None = None
    model: AgentModel | None = None


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
    id: str
    name: str
    urls: list[str]
    prompt: str
    schema_definition: dict[str, Any]
    schedule: str | None
    monitor_id: str | None
    status: ExtractorStatus
    health: ExtractorHealth
    model_preference: AgentModel
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = None
    run_count: int = 0
    success_rate: float = 0.0


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
