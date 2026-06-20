import asyncio
from datetime import datetime

from app.db import get_supabase_client
from app.models.db_models import (
    TABLE_EXTRACTORS,
    ExtractorHealth,
    ExtractorRow,
    ExtractorStatus,
)
from app.models.schemas import CreateExtractorRequest, ExtractorResponse, UpdateExtractorRequest
from app.repositories.runs import get_run_stats


class ExtractorNotFoundError(LookupError):
    def __init__(self, extractor_id: str) -> None:
        self.extractor_id = extractor_id
        super().__init__(f"Extractor not found: {extractor_id}")


def _row_to_response(
    row: ExtractorRow,
    *,
    last_run_at: datetime | None = None,
    run_count: int = 0,
    success_rate: float = 0.0,
) -> ExtractorResponse:
    return ExtractorResponse(
        id=row.id,
        name=row.name,
        urls=row.urls,
        prompt=row.prompt,
        schema_definition=row.schema_definition,
        schedule=row.schedule,
        monitor_id=row.monitor_id,
        status=row.status,
        health=row.health,
        model_preference=row.model_preference,
        consecutive_failures=row.consecutive_failures,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_run_at=last_run_at,
        run_count=run_count,
        success_rate=success_rate,
    )


def _insert_extractor(payload: CreateExtractorRequest) -> ExtractorRow:
    client = get_supabase_client()
    record = {
        "name": payload.name,
        "urls": payload.urls,
        "prompt": payload.prompt,
        "schema_definition": payload.schema_definition,
        "schedule": payload.schedule,
        "model_preference": payload.model.value,
        "status": ExtractorStatus.ACTIVE.value,
        "health": ExtractorHealth.HEALTHY.value,
        "consecutive_failures": 0,
    }

    response = (
        client.table(TABLE_EXTRACTORS)
        .insert(record)
        .select("*")
        .execute()
    )
    rows = response.data
    if not rows:
        raise RuntimeError("Insert did not return a row")
    return ExtractorRow.model_validate(rows[0])


def _list_extractors() -> list[ExtractorRow]:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTORS)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [ExtractorRow.model_validate(row) for row in response.data]


def _get_extractor(extractor_id: str) -> ExtractorRow:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTORS)
        .select("*")
        .eq("id", extractor_id)
        .execute()
    )
    rows = response.data
    if not rows:
        raise ExtractorNotFoundError(extractor_id)
    return ExtractorRow.model_validate(rows[0])


def _build_update_record(payload: UpdateExtractorRequest) -> dict:
    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.urls is not None:
        updates["urls"] = payload.urls
    if payload.prompt is not None:
        updates["prompt"] = payload.prompt
    if payload.schema_definition is not None:
        updates["schema_definition"] = payload.schema_definition
    if payload.schedule is not None:
        updates["schedule"] = payload.schedule
    if payload.status is not None:
        updates["status"] = payload.status.value
    if payload.model is not None:
        updates["model_preference"] = payload.model.value
    return updates


def _update_extractor(extractor_id: str, payload: UpdateExtractorRequest) -> ExtractorRow:
    updates = _build_update_record(payload)
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTORS)
        .update(updates)
        .eq("id", extractor_id)
        .select("*")
        .execute()
    )
    rows = response.data
    if not rows:
        raise ExtractorNotFoundError(extractor_id)
    return ExtractorRow.model_validate(rows[0])


def _delete_extractor(extractor_id: str) -> None:
    client = get_supabase_client()
    response = (
        client.table(TABLE_EXTRACTORS)
        .delete()
        .eq("id", extractor_id)
        .select("*")
        .execute()
    )
    if not response.data:
        raise ExtractorNotFoundError(extractor_id)


async def create_extractor(payload: CreateExtractorRequest) -> ExtractorResponse:
    row = await asyncio.to_thread(_insert_extractor, payload)
    return _row_to_response(row)


async def list_extractors() -> list[ExtractorResponse]:
    rows = await asyncio.to_thread(_list_extractors)
    responses: list[ExtractorResponse] = []
    for row in rows:
        last_run_at, run_count, success_rate = await get_run_stats(row.id)
        responses.append(
            _row_to_response(
                row,
                last_run_at=last_run_at,
                run_count=run_count,
                success_rate=success_rate,
            )
        )
    return responses


async def get_extractor(extractor_id: str) -> ExtractorResponse:
    row = await asyncio.to_thread(_get_extractor, extractor_id)
    last_run_at, run_count, success_rate = await get_run_stats(extractor_id)
    return _row_to_response(
        row,
        last_run_at=last_run_at,
        run_count=run_count,
        success_rate=success_rate,
    )


async def update_extractor(
    extractor_id: str,
    payload: UpdateExtractorRequest,
) -> ExtractorResponse:
    row = await asyncio.to_thread(_update_extractor, extractor_id, payload)
    return _row_to_response(row)


async def delete_extractor(extractor_id: str) -> None:
    await asyncio.to_thread(_delete_extractor, extractor_id)
