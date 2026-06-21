"""Step-by-step debug runner using Firecrawl /scrape + /interact."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.helpers.firecrawl import extract_scrape_id, get_attr
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


def _interact_response_ok(response: Any) -> tuple[bool, str | None]:
    success = get_attr(response, "success")
    if success is False:
        stderr = get_attr(response, "stderr", default="") or ""
        error = get_attr(response, "error")
        exit_code = get_attr(response, "exit_code", "exitCode")
        parts = [
            part for part in (error, stderr.strip(), f"exit_code={exit_code}") if part
        ]
        return False, " | ".join(str(part) for part in parts) or "Interact call failed"

    killed = get_attr(response, "killed")
    if killed:
        return False, "Interact call timed out"

    exit_code = get_attr(response, "exit_code", "exitCode")
    if exit_code not in (None, 0):
        stderr = get_attr(response, "stderr", default="") or ""
        return False, stderr.strip() or f"Interact exited with code {exit_code}"

    return True, None


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
            action_label = step.action_label()
            step_started = time.monotonic()

            try:
                response = client.interact(
                    scrape_id, code=step.code, language=language.value
                )
            except Exception as exc:
                duration_ms = int((time.monotonic() - step_started) * 1000)
                step_results.append(
                    StepResult(
                        index=index,
                        action=action_label,
                        status=StepStatus.FAILED,
                        duration_ms=duration_ms,
                        error=str(exc),
                    )
                )
                failed_at_step = index
                _append_skipped_steps(step_results, steps, index + 1)
                break

            ok, error = _interact_response_ok(response)
            duration_ms = int((time.monotonic() - step_started) * 1000)
            payload = response if isinstance(response, dict) else response.model_dump()

            if ok:
                step_results.append(
                    StepResult(
                        index=index,
                        action=action_label,
                        status=StepStatus.PASSED,
                        duration_ms=duration_ms,
                        output=payload.get("output"),
                        live_view_url=payload.get("liveViewUrl"),
                    )
                )
                continue

            step_results.append(
                StepResult(
                    index=index,
                    action=action_label,
                    status=StepStatus.FAILED,
                    duration_ms=duration_ms,
                    error=error,
                    output=payload.get("output"),
                    live_view_url=payload.get("liveViewUrl"),
                )
            )
            failed_at_step = index
            _append_skipped_steps(step_results, steps, index + 1)
            break

        if failed_at_step is None:
            try:
                content_response = client.interact(
                    scrape_id, **_page_content_kwargs(language)
                )
                ok, _ = _interact_response_ok(content_response)
                if ok:
                    content_payload = (
                        content_response
                        if isinstance(content_response, dict)
                        else content_response.model_dump()
                    )
                    page_content = content_payload.get("output")
            except Exception:
                pass

            if not page_content:
                payload = (
                    scrape_result.model_dump()
                    if hasattr(scrape_result, "model_dump")
                    else scrape_result
                )
                if isinstance(payload, dict):
                    page_content = payload.get("markdown")

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
