from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.services.firecrawl_client import FirecrawlNotConfiguredError, get_firecrawl_client

router = APIRouter()


class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapeResponse(BaseModel):
    url: str
    markdown: str | None = None
    metadata: dict | None = None


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(body: ScrapeRequest) -> ScrapeResponse:
    """Scrape a URL via Firecrawl and return markdown content."""
    try:
        client = get_firecrawl_client()
    except FirecrawlNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    url = str(body.url)

    try:
        document = client.scrape(url, formats=["markdown"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    data = document.model_dump()
    return ScrapeResponse(
        url=url,
        markdown=data.get("markdown"),
        metadata=data.get("metadata"),
    )
