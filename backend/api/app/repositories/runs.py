import asyncio
from datetime import datetime
from typing import Any

from app.db import get_supabase_client
from app.models.db_models import (
    TABLE_EXTRACTION_RUNS,
    ExtractionRunRow,
    RunStatus,
    RunTrigger,
)
from app.models.schemas import RunResponse


class RunNotFoundError(LookupError):
    def __init__(self, extractor_id: str, run_id: str) -> None:
        self.extractor_id = extractor_id
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id} (extractor {extractor_id})")


def _row_to_response(row: ExtractionRunRow) -> RunResponse:
    return RunResponse(
        id=row.id,
        extractor_id=row.extractor_id,
        status=row.status,
        trigger=row.trigger,
        started_at=row.started_at,
        completed_at=row.completed_at,
        duration_ms=row.duration_ms,
        data=row.data,
        validation_errors=row.validation_errors,
        was_repaired=row.was_repaired,
        credits_used=row.credits_used,
        error=row.error,
    )


def _insert_run(extractor_id: str, trigger: RunTrigger) -> ExtractionRunRow:
    client = get_supabase_client()
    record = {
        "extractor_id": extractor_id,
        "status": RunStatus.RUNNING.value,
        "trigger": trigger.value,
        "validation_errors": [],
        "was_repaired": False,
        "credits_used": 0,
    }
    response = (
        client.table(TABLE_EXTRACTION_RUNS)
        .insert(record)
        .select("*")
        .execute()
    )
    rows = response.data
    if not rows:
        raise RuntimeError("Failed to create extraction run")
    return ExtractionRunRow.model_validate(rows[0])


def _update_run(run_id: str, updates: dict[str, Any]) -> ExtractionRunRow:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTION_RUNS)
        .update(updates)
        .eq("id", run_id)
        .select("*")
        .execute()
    )
    rows = response.data
    if not rows:
        raise RuntimeError(f"Failed to update extraction run: {run_id}")
    return ExtractionRunRow.model_validate(rows[0])


def _get_run(extractor_id: str, run_id: str) -> ExtractionRunRow:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTION_RUNS)
        .select("*")
        .eq("id", run_id)
        .eq("extractor_id", extractor_id)
        .execute()
    )
    rows = response.data
    if not rows:
        raise RunNotFoundError(extractor_id, run_id)
    return ExtractionRunRow.model_validate(rows[0])


def _list_runs(extractor_id: str) -> list[ExtractionRunRow]:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTION_RUNS)
        .select("*")
        .eq("extractor_id", extractor_id)
        .order("started_at", desc=True)
        .execute()
    )
    return [ExtractionRunRow.model_validate(row) for row in response.data]


def _get_run_stats(extractor_id: str) -> tuple[datetime | None, int, float]:
    runs = _list_runs(extractor_id)
    if not runs:
        return None, 0, 0.0

    successful = sum(
        1
        for run in runs
        if run.status in (RunStatus.COMPLETED, RunStatus.REPAIRED)
    )
    success_rate = successful / len(runs)
    return runs[0].started_at, len(runs), success_rate


async def create_run(extractor_id: str, trigger: RunTrigger) -> ExtractionRunRow:
    return await asyncio.to_thread(_insert_run, extractor_id, trigger)


async def finalize_run(run_id: str, updates: dict[str, Any]) -> ExtractionRunRow:
    return await asyncio.to_thread(_update_run, run_id, updates)


async def get_run(extractor_id: str, run_id: str) -> RunResponse:
    row = await asyncio.to_thread(_get_run, extractor_id, run_id)
    return _row_to_response(row)


async def list_runs(extractor_id: str) -> list[RunResponse]:
    rows = await asyncio.to_thread(_list_runs, extractor_id)
    return [_row_to_response(row) for row in rows]


async def get_run_stats(
    extractor_id: str,
) -> tuple[datetime | None, int, float]:
    return await asyncio.to_thread(_get_run_stats, extractor_id)
