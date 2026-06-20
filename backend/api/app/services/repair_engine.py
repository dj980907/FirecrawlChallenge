import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.models.db_models import (
    AgentModel,
    ExtractorRow,
    RepairAttemptRow,
    RepairStrategy,
)
from app.models.schemas import RepairAttemptOut
from app.repositories.repair_attempts import create_repair_attempt, repair_attempt_to_out
from app.services.agent_runner import run_agent, scrape_urls_markdown
from app.services.schema_validator import validate_extraction


@dataclass
class RepairResult:
    succeeded: bool
    data: dict[str, Any] | None = None
    validation_errors: list[str] = field(default_factory=list)
    repair_attempts: list[RepairAttemptOut] = field(default_factory=list)
    credits_used: int = 0
    model_upgraded: bool = False


def _attempt_to_out(row: RepairAttemptRow) -> RepairAttemptOut:
    return repair_attempt_to_out(row)


def _missing_required_fields(
    schema: dict[str, Any],
    data: dict[str, Any] | None,
) -> list[str]:
    required = schema.get("required", [])
    if not isinstance(required, list):
        return []

    if not data:
        return [str(field) for field in required]

    return [str(field) for field in required if field not in data]


def _build_refined_prompt(
    extractor: ExtractorRow,
    validation_errors: list[str],
    original_data: dict[str, Any] | None,
) -> str:
    missing = _missing_required_fields(extractor.schema_definition, original_data)
    error_lines = "\n".join(f"- {error}" for error in validation_errors)
    missing_line = ", ".join(missing) if missing else "see validation errors above"

    return (
        f"{extractor.prompt}\n\n"
        "Previous extraction had these validation issues:\n"
        f"{error_lines}\n\n"
        f"The following required fields were missing or invalid: {missing_line}.\n"
        "Please extract these fields specifically and ensure the output matches "
        "the schema exactly."
    )


def _build_fresh_scrape_prompt(
    extractor: ExtractorRow,
    page_content: str,
) -> str:
    return (
        f"{extractor.prompt}\n\n"
        "Here is the current page content:\n"
        f"{page_content}"
    )


async def _execute_strategy(
    extractor: ExtractorRow,
    run_id: str,
    strategy: RepairStrategy,
    *,
    prompt: str,
    model: AgentModel | None = None,
) -> tuple[RepairAttemptOut, bool, dict[str, Any] | None, list[str], int]:
    import time

    started = time.monotonic()
    agent_error: str | None = None
    data: dict[str, Any] | None = None
    validation_errors: list[str] = []
    credits_used = 0

    try:
        _status, data, credits_used, agent_error = await asyncio.to_thread(
            run_agent,
            extractor,
            prompt=prompt,
            model=model,
        )
        if agent_error:
            validation_errors = [agent_error]
        elif data is None:
            validation_errors = ["No data returned from agent"]
        else:
            validation_errors = validate_extraction(data, extractor.schema_definition)
    except Exception as exc:
        agent_error = str(exc)
        validation_errors = [agent_error]

    succeeded = not validation_errors
    duration_ms = int((time.monotonic() - started) * 1000)

    attempt_row = await create_repair_attempt(
        run_id=run_id,
        strategy=strategy,
        succeeded=succeeded,
        prompt_used=prompt,
        model_used=(model or extractor.model_preference).value,
        data=data,
        error=agent_error if not succeeded else None,
        duration_ms=duration_ms,
        credits_used=credits_used,
    )

    return (
        _attempt_to_out(attempt_row),
        succeeded,
        data,
        validation_errors,
        credits_used,
    )


async def attempt_repair(
    extractor: ExtractorRow,
    run_id: str,
    validation_errors: list[str],
    original_data: dict[str, Any] | None,
) -> RepairResult:
    """
    Try up to three repair strategies in order, stopping at the first success.
    """
    attempts: list[RepairAttemptOut] = []
    total_credits = 0
    last_errors = list(validation_errors)
    model_upgraded = False

    refined_prompt = _build_refined_prompt(extractor, validation_errors, original_data)
    attempt, succeeded, data, errors, credits = await _execute_strategy(
        extractor,
        run_id,
        RepairStrategy.PROMPT_REFINEMENT,
        prompt=refined_prompt,
    )
    attempts.append(attempt)
    total_credits += credits
    if succeeded and data is not None:
        return RepairResult(
            succeeded=True,
            data=data,
            validation_errors=[],
            repair_attempts=attempts,
            credits_used=total_credits,
        )
    last_errors = errors

    if extractor.model_preference == AgentModel.SPARK_1_MINI:
        attempt, succeeded, data, errors, credits = await _execute_strategy(
            extractor,
            run_id,
            RepairStrategy.MODEL_UPGRADE,
            prompt=extractor.prompt,
            model=AgentModel.SPARK_1_PRO,
        )
        attempts.append(attempt)
        total_credits += credits
        if succeeded and data is not None:
            model_upgraded = True
            return RepairResult(
                succeeded=True,
                data=data,
                validation_errors=[],
                repair_attempts=attempts,
                credits_used=total_credits,
                model_upgraded=True,
            )
        last_errors = errors

    page_content = await asyncio.to_thread(scrape_urls_markdown, extractor.urls)
    fresh_prompt = _build_fresh_scrape_prompt(extractor, page_content)
    attempt, succeeded, data, errors, credits = await _execute_strategy(
        extractor,
        run_id,
        RepairStrategy.FRESH_SCRAPE,
        prompt=fresh_prompt,
    )
    attempts.append(attempt)
    total_credits += credits
    if succeeded and data is not None:
        return RepairResult(
            succeeded=True,
            data=data,
            validation_errors=[],
            repair_attempts=attempts,
            credits_used=total_credits,
        )

    return RepairResult(
        succeeded=False,
        data=original_data,
        validation_errors=errors or last_errors,
        repair_attempts=attempts,
        credits_used=total_credits,
        model_upgraded=model_upgraded,
    )
