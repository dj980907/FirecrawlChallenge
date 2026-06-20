from fastapi import APIRouter, HTTPException, status

from app.models.schemas import DebugRunRequest, DebugRunResponse
from app.services.debug_runner import run_debug_sequence_async
from app.services.firecrawl_client import FirecrawlNotConfiguredError

router = APIRouter()


@router.post("/debug-run", response_model=DebugRunResponse)
async def debug_run(body: DebugRunRequest) -> DebugRunResponse:
    """
    Run /interact steps one at a time and return a debug report.

    Each step is either a `prompt` or `code` string (same as Firecrawl /interact).
    On failure, returns the step index, error, live view URL, and a screenshot.
    """
    try:
        return await run_debug_sequence_async(str(body.url), body.steps)
    except FirecrawlNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
