import asyncio

from app.db import get_supabase_client
from app.models.db_models import (
    TABLE_EXTRACTORS,
    ExtractorHealth,
    ExtractorRow,
    ExtractorStatus,
)
from app.models.schemas import CreateExtractorRequest, ExtractorResponse


def _row_to_response(row: ExtractorRow) -> ExtractorResponse:
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


async def create_extractor(payload: CreateExtractorRequest) -> ExtractorResponse:
    row = await asyncio.to_thread(_insert_extractor, payload)
    return _row_to_response(row)


async def list_extractors() -> list[ExtractorResponse]:
    rows = await asyncio.to_thread(_list_extractors)
    return [_row_to_response(row) for row in rows]
