"""Helpers for parsing Firecrawl API responses."""

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
