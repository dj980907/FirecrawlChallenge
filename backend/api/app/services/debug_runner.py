"""Step-by-step debug runner using Firecrawl /scrape + /interact."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.helpers.firecrawl import (
    evaluate_interact_response,
    extract_scrape_id,
    interact_payload,
)
from app.models.schemas import (
    DebugRunResponse,
    DebugRunStatus,
    DebugStep,
    InteractLanguage,
    StepResult,
    StepStatus,
)
from app.services.firecrawl_client import get_firecrawl_client

PAGE_CONTENT_SNIPPETS: dict[InteractLanguage, str] = {
    InteractLanguage.NODE: """
const body = await page.locator('body').innerText();
body;
""".strip(),
    InteractLanguage.PYTHON: """
body = await page.locator("body").inner_text()
body
""".strip(),
    InteractLanguage.BASH: "agent-browser scrape",
}


def _resolve_language(steps: list[DebugStep]) -> InteractLanguage:
    for step in steps:
        if step.language:
            return step.language
    return InteractLanguage.NODE


def _page_content_kwargs(language: InteractLanguage) -> dict[str, Any]:
    if language == InteractLanguage.BASH:
        return {"code": PAGE_CONTENT_SNIPPETS[language], "language": "bash"}
    if language == InteractLanguage.PYTHON:
        return {"code": PAGE_CONTENT_SNIPPETS[language], "language": "python"}
    return {"code": PAGE_CONTENT_SNIPPETS[InteractLanguage.NODE]}


def _append_skipped_steps(
    steps: list[StepResult],
    all_steps: list[DebugStep],
    start_index: int,
) -> None:
    for skip_index in range(start_index, len(all_steps) + 1):
        steps.append(
            StepResult(
                index=skip_index,
                action=all_steps[skip_index - 1].action_label(),
                status=StepStatus.SKIPPED,
                duration_ms=0,
            )
        )


@dataclass(frozen=True)
class _StepOutcome:
    result: StepResult
    failed: bool


def _execute_step(
    client: Any,
    scrape_id: str,
    *,
    index: int,
    step: DebugStep,
    language: InteractLanguage,
) -> _StepOutcome:
    action_label = step.action_label()
    step_started = time.monotonic()

    try:
        response = client.interact(
            scrape_id, code=step.code, language=language.value
        )
    except Exception as exc:
        return _StepOutcome(
            result=StepResult(
                index=index,
                action=action_label,
                status=StepStatus.FAILED,
                duration_ms=int((time.monotonic() - step_started) * 1000),
                error=str(exc),
            ),
            failed=True,
        )

    evaluation = evaluate_interact_response(response)
    payload = interact_payload(response)
    print("this is the response", response)
    print("this is the payload", payload)
    duration_ms = int((time.monotonic() - step_started) * 1000)

    if evaluation.ok:
        return _StepOutcome(
            result=StepResult(
                index=index,
                action=action_label,
                status=StepStatus.PASSED,
                duration_ms=duration_ms,
                output=payload.get("output"),
                live_view_url=payload.get("live_view_url"),
            ),
            failed=False,
        )

    return _StepOutcome(
        result=StepResult(
            index=index,
            action=action_label,
            status=StepStatus.FAILED,
            duration_ms=duration_ms,
            error=evaluation.error,
            output=payload.get("output"),
            live_view_url=payload.get("live_view_url"),
        ),
        failed=True,
    )


def _fetch_page_content(
    client: Any,
    scrape_id: str,
    *,
    language: InteractLanguage,
    scrape_result: Any,
) -> str | None:
    try:
        response = client.interact(scrape_id, **_page_content_kwargs(language))
        evaluation = evaluate_interact_response(response)
        if evaluation.ok:
            output = interact_payload(response).get("output")
            if output is not None:
                return str(output)
    except Exception:
        pass

    payload = (
        scrape_result.model_dump()
        if hasattr(scrape_result, "model_dump")
        else scrape_result
    )
    if isinstance(payload, dict):
        return payload.get("markdown")
    return None


def run_debug_sequence(
    url: str,
    steps: list[DebugStep],
    *,
    parsed_steps: list[str] | None = None,
    step_summaries: list[str] | None = None,
) -> DebugRunResponse:
    """
    Execute each /interact step individually and return a debug report.

    On the first failure, skip remaining steps.
    """
    client = get_firecrawl_client()
    scrape_id: str | None = None
    started = time.monotonic()
    step_results: list[StepResult] = []
    failed_at_step: int | None = None
    page_content: str | None = None
    language = _resolve_language(steps)

    try:
        scrape_result = client.scrape(url, formats=["markdown"])
        scrape_id = extract_scrape_id(scrape_result)

        for index, step in enumerate(steps, start=1):
            outcome = _execute_step(
                client,
                scrape_id,
                index=index,
                step=step,
                language=language,
            )
            step_results.append(outcome.result)
            if outcome.failed:
                failed_at_step = index
                _append_skipped_steps(step_results, steps, index + 1)
                break

        if failed_at_step is None:
            page_content = _fetch_page_content(
                client,
                scrape_id,
                language=language,
                scrape_result=scrape_result,
            )

    finally:
        if scrape_id:
            client.stop_interaction(scrape_id)

    total_duration_ms = int((time.monotonic() - started) * 1000)
    status = DebugRunStatus.FAILED if failed_at_step else DebugRunStatus.COMPLETED

    return DebugRunResponse(
        status=status,
        failed_at_step=failed_at_step,
        total_steps=len(steps),
        total_duration_ms=total_duration_ms,
        steps=step_results,
        page_content=page_content,
        scrape_id=scrape_id,
        parsed_steps=parsed_steps,
        step_summaries=step_summaries,
    )


async def run_debug_sequence_async(
    url: str,
    steps: list[DebugStep],
    *,
    parsed_steps: list[str] | None = None,
    step_summaries: list[str] | None = None,
) -> DebugRunResponse:
    return await asyncio.to_thread(
        run_debug_sequence,
        url,
        steps,
        parsed_steps=parsed_steps,
        step_summaries=step_summaries,
    )
