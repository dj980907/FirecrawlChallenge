import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.models.db_models import ExtractorRow, RunStatus, RunTrigger
from app.models.schemas import RunResponse
from app.repositories.extractors import _get_extractor
from app.repositories.runs import create_run, finalize_run
from app.services.firecrawl_client import (
    FirecrawlNotConfiguredError,
    get_firecrawl_client,
)


def _normalize_agent_data(data: Any) -> dict[str, Any] | None:
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return {"value": data}


def _run_agent(
    extractor: ExtractorRow,
) -> tuple[RunStatus, dict[str, Any] | None, int, str | None]:
    client = get_firecrawl_client()
    timeout = int(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))

    response = client.agent(
        urls=extractor.urls,
        prompt=extractor.prompt,
        schema=extractor.schema_definition,
        model=extractor.model_preference.value,
        timeout=timeout,
        # i don't really want this to be extreme lol
        max_credits=20,
    )

    credits_used = response.credits_used or 0
    data = _normalize_agent_data(response.data)

    if response.status == "completed" and data is not None:
        return RunStatus.COMPLETED, data, credits_used, None

    error = response.error or f"Agent finished with status: {response.status}"
    return RunStatus.FAILED, data, credits_used, error


async def run_extraction(
    extractor_id: str,
    *,
    trigger: RunTrigger = RunTrigger.MANUAL,
) -> RunResponse:
    extractor = await asyncio.to_thread(_get_extractor, extractor_id)
    run = await create_run(extractor_id, trigger)
    started = time.monotonic()

    try:
        status, data, credits_used, error = await asyncio.to_thread(
            _run_agent, extractor
        )
    except FirecrawlNotConfiguredError:
        raise
    except Exception as exc:
        status = RunStatus.FAILED
        data = None
        credits_used = 0
        error = str(exc)

    duration_ms = int((time.monotonic() - started) * 1000)
    completed_at = datetime.now(timezone.utc)

    updated = await finalize_run(
        run.id,
        {
            "status": status.value,
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "data": data,
            "credits_used": credits_used,
            "error": error,
        },
    )

    return RunResponse(
        id=updated.id,
        extractor_id=updated.extractor_id,
        status=updated.status,
        trigger=updated.trigger,
        started_at=updated.started_at,
        completed_at=updated.completed_at,
        duration_ms=updated.duration_ms,
        data=updated.data,
        validation_errors=updated.validation_errors,
        was_repaired=updated.was_repaired,
        credits_used=updated.credits_used,
        error=updated.error,
    )
