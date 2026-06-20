from fastapi import APIRouter, HTTPException, status

from app.db import SupabaseNotConfiguredError
from app.models.schemas import CreateExtractorRequest, ExtractorResponse
from app.repositories.extractors import create_extractor, list_extractors

router = APIRouter(
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Supabase request failed",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set",
        },
    },
)


@router.get(
    "",
    response_model=list[ExtractorResponse],
    summary="List extractors",
    response_description="All extractors, newest first",
)
async def list_extractors_endpoint() -> list[ExtractorResponse]:
    """
    Return every managed extractor stored in Supabase.

    Results are ordered by `created_at` descending. Run stats (`last_run_at`,
    `run_count`, `success_rate`) are placeholders until extraction runs are
    implemented.
    """
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


@router.post(
    "",
    response_model=ExtractorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create extractor",
    response_description="The created extractor record",
)
async def create_extractor_endpoint(body: CreateExtractorRequest) -> ExtractorResponse:
    """
    Register a new managed extractor.

    Persists the configuration (URLs, prompt, JSON schema) to Supabase with
    `status=active` and `health=healthy`. Does **not** call Firecrawl yet —
    no test extraction or monitor setup at this stage.

    Use `schema_definition` as a standard JSON Schema object. Required fields
    in the schema are enforced later when extraction runs.
    """
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
