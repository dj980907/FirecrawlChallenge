from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    CodeDebugRunRequest,
    DebugRunResponse,
    DebugStep,
    MixedDebugRunRequest,
    PromptDebugRunRequest,
)
from app.services.debug_runner import run_debug_sequence_async
from app.services.firecrawl_client import FirecrawlNotConfiguredError

router = APIRouter()


async def _run_debug(url: str, steps: list[DebugStep]) -> DebugRunResponse:
    try:
        return await run_debug_sequence_async(url, steps)
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


@router.post("/debug-run/code", response_model=DebugRunResponse)
async def debug_run_code(body: CodeDebugRunRequest) -> DebugRunResponse:
    """
    Run a sequence of /interact **code** steps and return a debug report.

    Every step must be `{ "code": "...", "language": "bash" }` (language optional).
    """
    steps = [step.to_debug_step() for step in body.steps]
    return await _run_debug(str(body.url), steps)


@router.post("/debug-run/prompt", response_model=DebugRunResponse)
async def debug_run_prompt(body: PromptDebugRunRequest) -> DebugRunResponse:
    """
    Run a sequence of /interact **prompt** steps and return a debug report.

    Every step must be `{ "prompt": "..." }`.
    """
    steps = [step.to_debug_step() for step in body.steps]
    return await _run_debug(str(body.url), steps)


@router.post("/debug-run/mixed", response_model=DebugRunResponse)
async def debug_run_mixed(body: MixedDebugRunRequest) -> DebugRunResponse:
    """
    Run a mixed sequence of /interact **prompt** and **code** steps.

    Each step is either `{ "prompt": "..." }` or `{ "code": "..." }`.
    """
    steps = [step.to_debug_step() for step in body.steps]
    return await _run_debug(str(body.url), steps)
