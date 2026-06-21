from fastapi import HTTPException, status

from app.models.schemas import DebugRunResponse, DebugStep
from app.services.debug_runner import run_debug_sequence_async
from app.services.firecrawl_client import FirecrawlNotConfiguredError


async def run_debug(
    url: str,
    steps: list[DebugStep],
    *,
    parsed_steps: list[str] | None = None,
    step_summaries: list[str] | None = None,
) -> DebugRunResponse:
    try:
        return await run_debug_sequence_async(
            url,
            steps,
            parsed_steps=parsed_steps,
            step_summaries=step_summaries,
        )
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
