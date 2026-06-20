import os
from typing import Any

from app.models.db_models import AgentModel, ExtractorRow, RunStatus
from app.services.firecrawl_client import get_firecrawl_client


def normalize_agent_data(data: Any) -> dict[str, Any] | None:
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return {"value": data}


def run_agent(
    extractor: ExtractorRow,
    *,
    prompt: str | None = None,
    model: AgentModel | None = None,
) -> tuple[RunStatus, dict[str, Any] | None, int, str | None]:
    client = get_firecrawl_client()
    timeout = int(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))

    response = client.agent(
        urls=extractor.urls,
        prompt=prompt or extractor.prompt,
        schema=extractor.schema_definition,
        model=(model or extractor.model_preference).value,
        timeout=timeout,
        max_credits=20,
    )

    credits_used = response.credits_used or 0
    data = normalize_agent_data(response.data)

    if response.status == "completed" and data is not None:
        return RunStatus.COMPLETED, data, credits_used, None

    error = response.error or f"Agent finished with status: {response.status}"
    return RunStatus.FAILED, data, credits_used, error


def scrape_urls_markdown(urls: list[str]) -> str:
    client = get_firecrawl_client()
    sections: list[str] = []

    for url in urls:
        document = client.scrape(url, formats=["markdown"])
        payload = document.model_dump() if hasattr(document, "model_dump") else document
        markdown = payload.get("markdown") or ""
        sections.append(f"URL: {url}\n{markdown}")

    return "\n\n---\n\n".join(sections)
