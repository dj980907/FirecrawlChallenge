"""Step-by-step debug runner using Firecrawl /scrape + /interact."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.models.schemas import (
    DebugRunResponse,
    DebugRunStatus,
    DebugStep,
    StepResult,
    StepStatus,
)
from app.services.firecrawl_client import get_firecrawl_client

SCREENSHOT_CODE = """
const buf = await page.screenshot({ fullPage: false });
buf.toString('base64');
""".strip()

PAGE_CONTENT_CODE = """
const body = await page.locator('body').innerText();
body;
""".strip()


def _get_attr(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _extract_scrape_id(scrape_result: Any) -> str:
    metadata = _get_attr(scrape_result, "metadata")
    scrape_id = _get_attr(metadata, "scrape_id", "scrapeId")
    if scrape_id:
        return str(scrape_id)

    payload = scrape_result.model_dump() if hasattr(scrape_result, "model_dump") else scrape_result
    if isinstance(payload, dict):
        meta = payload.get("metadata") or {}
        if isinstance(meta, dict):
            found = meta.get("scrape_id") or meta.get("scrapeId")
            if found:
                return str(found)

    raise RuntimeError("Firecrawl scrape did not return a scrape_id for /interact")


def _interact_response_ok(response: Any) -> tuple[bool, str | None]:
    success = _get_attr(response, "success")
    if success is False:
        stderr = _get_attr(response, "stderr", default="") or ""
        error = _get_attr(response, "error")
        exit_code = _get_attr(response, "exit_code", "exitCode")
        parts = [part for part in (error, stderr.strip(), f"exit_code={exit_code}") if part]
        return False, " | ".join(str(part) for part in parts) or "Interact call failed"

    killed = _get_attr(response, "killed")
    if killed:
        return False, "Interact call timed out"

    exit_code = _get_attr(response, "exit_code", "exitCode")
    if exit_code not in (None, 0):
        stderr = _get_attr(response, "stderr", default="") or ""
        return False, stderr.strip() or f"Interact exited with code {exit_code}"

    return True, None


def _run_interact(client: Any, scrape_id: str, step: DebugStep) -> Any:
    if step.prompt:
        return client.interact(scrape_id, prompt=step.prompt)
    kwargs: dict[str, Any] = {"code": step.code}
    if step.language:
        kwargs["language"] = step.language
    return client.interact(scrape_id, **kwargs)


def _step_fields_from_response(response: Any) -> dict[str, str | None]:
    output = _get_attr(response, "output")
    live_view = _get_attr(response, "live_view_url", "liveViewUrl")
    return {
        "output": str(output) if output is not None else None,
        "live_view_url": str(live_view) if live_view else None,
    }


def _capture_screenshot(client: Any, scrape_id: str) -> str | None:
    try:
        shot = client.interact(scrape_id, code=SCREENSHOT_CODE)
        ok, _ = _interact_response_ok(shot)
        if ok:
            result = _get_attr(shot, "result")
            return str(result) if result is not None else None
    except Exception:
        pass
    return None


def _stop_session(client: Any, scrape_id: str | None) -> None:
    if not scrape_id:
        return
    try:
        client.stop_interaction(scrape_id)
    except Exception:
        pass


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


def run_debug_sequence(url: str, steps: list[DebugStep]) -> DebugRunResponse:
    """
    Execute each /interact step individually and return a debug report.

    On the first failure, capture a screenshot and skip remaining steps.
    """
    client = get_firecrawl_client()
    scrape_id: str | None = None
    started = time.monotonic()
    step_results: list[StepResult] = []
    failed_at_step: int | None = None
    page_content: str | None = None

    try:
        scrape_result = client.scrape(url, formats=["markdown"])
        scrape_id = _extract_scrape_id(scrape_result)

        for index, step in enumerate(steps, start=1):
            action_label = step.action_label()
            step_started = time.monotonic()

            try:
                response = _run_interact(client, scrape_id, step)
            except Exception as exc:
                duration_ms = int((time.monotonic() - step_started) * 1000)
                step_results.append(
                    StepResult(
                        index=index,
                        action=action_label,
                        status=StepStatus.FAILED,
                        duration_ms=duration_ms,
                        error=str(exc),
                        screenshot_base64=_capture_screenshot(client, scrape_id),
                    )
                )
                failed_at_step = index
                _append_skipped_steps(step_results, steps, index + 1)
                break

            fields = _step_fields_from_response(response)
            ok, error = _interact_response_ok(response)
            duration_ms = int((time.monotonic() - step_started) * 1000)

            if ok:
                step_results.append(
                    StepResult(
                        index=index,
                        action=action_label,
                        status=StepStatus.PASSED,
                        duration_ms=duration_ms,
                        output=fields["output"],
                        live_view_url=fields["live_view_url"],
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
                    output=fields["output"],
                    live_view_url=fields["live_view_url"],
                    screenshot_base64=_capture_screenshot(client, scrape_id),
                )
            )
            failed_at_step = index
            _append_skipped_steps(step_results, steps, index + 1)
            break

        if failed_at_step is None:
            try:
                content_response = client.interact(scrape_id, code=PAGE_CONTENT_CODE)
                ok, _ = _interact_response_ok(content_response)
                if ok:
                    result = _get_attr(content_response, "result")
                    if result is not None:
                        page_content = str(result)
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
        _stop_session(client, scrape_id)

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
    )


async def run_debug_sequence_async(url: str, steps: list[DebugStep]) -> DebugRunResponse:
    return await asyncio.to_thread(run_debug_sequence, url, steps)
