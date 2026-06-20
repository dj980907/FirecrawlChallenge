from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db import SupabaseNotConfiguredError
from app.models.schemas import CreateExtractorRequest, ExtractorResponse, UpdateExtractorRequest
from app.repositories.extractors import (
    ExtractorNotFoundError,
    create_extractor,
    delete_extractor,
    get_extractor,
    list_extractors,
    update_extractor,
)

router = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Extractor not found",
        },
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
