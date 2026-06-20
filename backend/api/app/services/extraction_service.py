import asyncio
import time
from datetime import datetime, timezone

from app.models.db_models import AgentModel, RunStatus, RunTrigger
from app.models.schemas import RunResponse
from app.repositories.extractors import _get_extractor, record_run_outcome, update_model_preference
from app.repositories.runs import create_run, finalize_run
from app.services.agent_runner import run_agent
from app.services.firecrawl_client import FirecrawlNotConfiguredError
from app.services.repair_engine import attempt_repair
from app.services.schema_validator import validate_extraction


async def run_extraction(
    extractor_id: str,
    *,
    trigger: RunTrigger = RunTrigger.MANUAL,
) -> RunResponse:
    extractor = await asyncio.to_thread(_get_extractor, extractor_id)
    run = await create_run(extractor_id, trigger)
    started = time.monotonic()

    repair_attempts = []
    was_repaired = False

    try:
        status, data, credits_used, error = await asyncio.to_thread(
            run_agent, extractor
        )
    except FirecrawlNotConfiguredError:
        raise
    except Exception as exc:
        status = RunStatus.FAILED
        data = None
        credits_used = 0
        error = str(exc)

    validation_errors: list[str] = []
    if status == RunStatus.COMPLETED:
        validation_errors = validate_extraction(data, extractor.schema_definition)
        if validation_errors:
            try:
                repair_result = await attempt_repair(
                    extractor,
                    run.id,
                    validation_errors,
                    data,
                )
            except FirecrawlNotConfiguredError:
                raise

            repair_attempts = repair_result.repair_attempts
            credits_used += repair_result.credits_used

            if repair_result.succeeded and repair_result.data is not None:
                status = RunStatus.REPAIRED
                data = repair_result.data
                validation_errors = []
                was_repaired = True
                error = None
                if repair_result.model_upgraded:
                    await update_model_preference(
                        extractor_id,
                        AgentModel.SPARK_1_PRO,
                    )
            else:
                status = RunStatus.FAILED
                validation_errors = repair_result.validation_errors
                if len(validation_errors) == 1:
                    error = (
                        "Schema validation failed and auto-repair exhausted: "
                        f"{validation_errors[0]}"
                    )
                else:
                    error = (
                        "Schema validation failed and auto-repair exhausted "
                        f"({len(validation_errors)} errors)"
                    )

    duration_ms = int((time.monotonic() - started) * 1000)
    completed_at = datetime.now(timezone.utc)

    run_succeeded = status in (RunStatus.COMPLETED, RunStatus.REPAIRED)
    await record_run_outcome(extractor_id, succeeded=run_succeeded)

    updated = await finalize_run(
        run.id,
        {
            "status": status.value,
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "data": data,
            "validation_errors": validation_errors,
            "was_repaired": was_repaired,
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
        drift_signals=[],
        repair_attempts=repair_attempts,
        was_repaired=updated.was_repaired,
        credits_used=updated.credits_used,
        error=updated.error,
    )
