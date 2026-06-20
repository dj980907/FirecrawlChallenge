import asyncio
from typing import Any

from app.db import get_supabase_client
from app.models.db_models import TABLE_REPAIR_ATTEMPTS, RepairAttemptRow, RepairStrategy
from app.models.schemas import RepairAttemptOut


def repair_attempt_to_out(row: RepairAttemptRow) -> RepairAttemptOut:
    return RepairAttemptOut(
        id=row.id,
        run_id=row.run_id,
        strategy=row.strategy,
        succeeded=row.succeeded,
        prompt_used=row.prompt_used,
        model_used=row.model_used,
        data=row.data,
        error=row.error,
        duration_ms=row.duration_ms,
        credits_used=row.credits_used,
    )


def _insert_repair_attempt(
    *,
    run_id: str,
    strategy: RepairStrategy,
    succeeded: bool,
    prompt_used: str | None,
    model_used: str | None,
    data: dict[str, Any] | None,
    error: str | None,
    duration_ms: int,
    credits_used: int,
) -> RepairAttemptRow:
    client = get_supabase_client()
    record = {
        "run_id": run_id,
        "strategy": strategy.value,
        "succeeded": succeeded,
        "prompt_used": prompt_used,
        "model_used": model_used,
        "data": data,
        "error": error,
        "duration_ms": duration_ms,
        "credits_used": credits_used,
    }
    response = (
        client.table(TABLE_REPAIR_ATTEMPTS)
        .insert(record)
        .select("*")
        .execute()
    )
    rows = response.data
    if not rows:
        raise RuntimeError("Failed to create repair attempt")
    return RepairAttemptRow.model_validate(rows[0])


def _list_repair_attempts(run_id: str) -> list[RepairAttemptRow]:
    client = get_supabase_client()
    response = (
        client.table(TABLE_REPAIR_ATTEMPTS)
        .select("*")
        .eq("run_id", run_id)
        .order("id")
        .execute()
    )
    return [RepairAttemptRow.model_validate(row) for row in response.data]


async def create_repair_attempt(
    *,
    run_id: str,
    strategy: RepairStrategy,
    succeeded: bool,
    prompt_used: str | None,
    model_used: str | None,
    data: dict[str, Any] | None,
    error: str | None,
    duration_ms: int,
    credits_used: int,
) -> RepairAttemptRow:
    return await asyncio.to_thread(
        _insert_repair_attempt,
        run_id=run_id,
        strategy=strategy,
        succeeded=succeeded,
        prompt_used=prompt_used,
        model_used=model_used,
        data=data,
        error=error,
        duration_ms=duration_ms,
        credits_used=credits_used,
    )


async def list_repair_attempts(run_id: str) -> list[RepairAttemptRow]:
    return await asyncio.to_thread(_list_repair_attempts, run_id)
