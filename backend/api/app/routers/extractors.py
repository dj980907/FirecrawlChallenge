from fastapi import APIRouter, HTTPException, status

from app.db import SupabaseNotConfiguredError
from app.models.schemas import CreateExtractorRequest, ExtractorResponse
from app.repositories.extractors import create_extractor, list_extractors

router = APIRouter()


@router.get("", response_model=list[ExtractorResponse])
async def list_extractors_endpoint() -> list[ExtractorResponse]:
    """List all managed extractors."""
    try:
        return await list_extractors()
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list extractors: {exc}",
        ) from exc


@router.post("", response_model=ExtractorResponse, status_code=status.HTTP_201_CREATED)
async def create_extractor_endpoint(body: CreateExtractorRequest) -> ExtractorResponse:
    """Create a managed extractor configuration (no Firecrawl run yet)."""
    try:
        return await create_extractor(body)
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create extractor: {exc}",
        ) from exc
