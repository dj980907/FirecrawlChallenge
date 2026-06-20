"""Table names and row shapes for Supabase Postgres."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

TABLE_EXTRACTORS = "extractors"
TABLE_EXTRACTION_RUNS = "extraction_runs"
TABLE_DRIFT_SIGNALS = "drift_signals"
TABLE_REPAIR_ATTEMPTS = "repair_attempts"


class ExtractorStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class ExtractorHealth(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REPAIRED = "repaired"


class RunTrigger(StrEnum):
    MANUAL = "manual"
    MONITOR = "monitor"


class DriftSignalType(StrEnum):
    MISSING_FIELD = "missing_field"
    TYPE_CHANGE = "type_change"
    EMPTY_VALUE = "empty_value"
    VALUE_ANOMALY = "value_anomaly"
    NEW_FIELD = "new_field"


class DriftSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RepairStrategy(StrEnum):
    PROMPT_REFINEMENT = "prompt_refinement"
    MODEL_UPGRADE = "model_upgrade"
    FRESH_SCRAPE = "fresh_scrape"


class AgentModel(StrEnum):
    SPARK_1_MINI = "spark-1-mini"
    SPARK_1_PRO = "spark-1-pro"


class ExtractorRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    urls: list[str]
    prompt: str
    schema_definition: dict[str, Any]
    schedule: str | None = None
    monitor_id: str | None = None
    status: ExtractorStatus = ExtractorStatus.ACTIVE
    health: ExtractorHealth = ExtractorHealth.HEALTHY
    model_preference: AgentModel = AgentModel.SPARK_1_MINI
    consecutive_failures: int = 0
    created_at: datetime
    updated_at: datetime


class ExtractionRunRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    extractor_id: str
    status: RunStatus
    trigger: RunTrigger = RunTrigger.MANUAL
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    data: dict[str, Any] | None = None
    validation_errors: list[str] = Field(default_factory=list)
    was_repaired: bool = False
    credits_used: int = 0
    error: str | None = None


class DriftSignalRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    run_id: str
    field: str
    signal_type: DriftSignalType
    expected: str
    actual: str
    severity: DriftSeverity


class RepairAttemptRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    run_id: str
    strategy: RepairStrategy
    succeeded: bool
    prompt_used: str | None = None
    model_used: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0
    credits_used: int = 0
