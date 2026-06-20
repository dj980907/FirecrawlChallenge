from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db import SupabaseNotConfiguredError
from app.models.schemas import (
    CreateExtractorRequest,
    ExtractorResponse,
    RunResponse,
    UpdateExtractorRequest,
)
from app.repositories.extractors import (
    ExtractorNotFoundError,
    create_extractor,
    delete_extractor,
    get_extractor,
    list_extractors,
    update_extractor,
)
from app.repositories.runs import RunNotFoundError, get_run, list_runs
from app.services.extraction_service import run_extraction
from app.services.firecrawl_client import FirecrawlNotConfiguredError

router = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Extractor not found",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Supabase request failed",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or FIRECRAWL_API_KEY not set",
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

    Results are ordered by `created_at` descending. Each extractor includes
    run stats (`last_run_at`, `run_count`, `success_rate`) when available.
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


@router.get(
    "/{extractor_id}",
    response_model=ExtractorResponse,
    summary="Get extractor",
    response_description="A single extractor by ID",
)
async def get_extractor_endpoint(extractor_id: UUID) -> ExtractorResponse:
    """
    Return one managed extractor by UUID.

    Returns `404` if no extractor exists with the given ID.
    """
    try:
        return await get_extractor(str(extractor_id))
    except ExtractorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get extractor: {exc}",
        ) from exc


@router.put(
    "/{extractor_id}",
    response_model=ExtractorResponse,
    summary="Update extractor",
    response_description="The updated extractor record",
)
async def update_extractor_endpoint(
    extractor_id: UUID,
    body: UpdateExtractorRequest,
) -> ExtractorResponse:
    """
    Partially update a managed extractor.

    Only fields present in the request body are changed. `updated_at` is
    refreshed automatically by the database trigger.

    Returns `404` if no extractor exists with the given ID.
    """
    try:
        return await update_extractor(str(extractor_id), body)
    except ExtractorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update extractor: {exc}",
        ) from exc


@router.delete(
    "/{extractor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete extractor",
    response_description="Extractor deleted",
)
async def delete_extractor_endpoint(extractor_id: UUID) -> None:
    """
    Delete a managed extractor and its related runs (cascade).

    Returns `404` if no extractor exists with the given ID.
    """
    try:
        await delete_extractor(str(extractor_id))
    except ExtractorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete extractor: {exc}",
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


@router.post(
    "/{extractor_id}/run",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run extraction",
    response_description="Extraction run result from Firecrawl agent",
)
async def run_extractor_endpoint(extractor_id: UUID) -> RunResponse:
    """
    Trigger a Firecrawl agent extraction for this extractor.

    Calls `/agent` with the extractor's URLs, prompt, and schema, validates the
    output against `schema_definition`, then stores the result in
    `extraction_runs`. Auto-repair is not implemented yet — failed validation
    marks the run as `failed` with `validation_errors` populated.

    Agent jobs can take several minutes. Timeout defaults to 300s
    (`AGENT_TIMEOUT_SECONDS` env var).
    """
    try:
        return await run_extraction(str(extractor_id))
    except ExtractorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except FirecrawlNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to run extraction: {exc}",
        ) from exc


@router.get(
    "/{extractor_id}/runs",
    response_model=list[RunResponse],
    summary="List extraction runs",
    response_description="Run history for an extractor, newest first",
)
async def list_runs_endpoint(extractor_id: UUID) -> list[RunResponse]:
    """Return all extraction runs for an extractor."""
    try:
        await get_extractor(str(extractor_id))
        return await list_runs(str(extractor_id))
    except ExtractorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list runs: {exc}",
        ) from exc


@router.get(
    "/{extractor_id}/runs/{run_id}",
    response_model=RunResponse,
    summary="Get extraction run",
    response_description="A single extraction run by ID",
)
async def get_run_endpoint(extractor_id: UUID, run_id: UUID) -> RunResponse:
    """Return one extraction run for an extractor."""
    try:
        return await get_run(str(extractor_id), str(run_id))
    except RunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get run: {exc}",
        ) from exc
