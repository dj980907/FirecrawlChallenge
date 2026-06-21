"""Helpers for parsing Firecrawl API responses."""

from dataclasses import dataclass
from typing import Any


def get_attr(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def extract_scrape_id(scrape_result: Any) -> str:
    """Return the scrape session ID needed for subsequent /interact calls."""
    metadata = get_attr(scrape_result, "metadata")
    scrape_id = get_attr(metadata, "scrape_id", "scrapeId")
    if scrape_id:
        return str(scrape_id)

    payload = (
        scrape_result.model_dump()
        if hasattr(scrape_result, "model_dump")
        else scrape_result
    )
    if isinstance(payload, dict):
        meta = payload.get("metadata") or {}
        if isinstance(meta, dict):
            found = meta.get("scrape_id") or meta.get("scrapeId")
            if found:
                return str(found)

    raise RuntimeError("Firecrawl scrape did not return a scrape_id for /interact")


def interact_payload(response: Any) -> dict[str, Any]:
    return response if isinstance(response, dict) else response.model_dump()


@dataclass(frozen=True)
class InteractResponseEvaluation:
    ok: bool
    error: str | None = None


def evaluate_interact_response(response: Any) -> InteractResponseEvaluation:
    """Determine whether a Firecrawl /interact call succeeded."""
    payload = interact_payload(response)

    if payload.get("killed"):
        return InteractResponseEvaluation(ok=False, error="Interact call timed out")

    if payload.get("success") is not False and payload.get("exitCode", 0) in (None, 0):
        return InteractResponseEvaluation(ok=True)

    stderr = (payload.get("stderr") or "").strip()
    error = payload.get("error")
    exit_code = payload.get("exitCode")
    parts = [
        part
        for part in (
            error,
            stderr or None,
            f"exit_code={exit_code}" if exit_code not in (None, 0) else None,
        )
        if part
    ]
    message = " | ".join(str(part) for part in parts) or "Interact call failed"
    return InteractResponseEvaluation(ok=False, error=message)
