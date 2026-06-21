from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    CodeBlockDebugRunRequest,
    CodeDebugRunRequest,
    DebugRunResponse,
    DebugStep,
    MixedDebugRunRequest,
    PromptDebugRunRequest,
)
from app.services.code_splitter import (
    AnthropicNotConfiguredError,
    CodeSplitError,
    split_code_block,
)
from app.services.debug_runner import run_debug_sequence_async
from app.services.firecrawl_client import FirecrawlNotConfiguredError

router = APIRouter()


async def _run_debug(
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


@router.post("/debug-run/code", response_model=DebugRunResponse)
async def debug_run_code(body: CodeDebugRunRequest) -> DebugRunResponse:
    """
    Run a sequence of /interact **code** steps and return a debug report.

    Every step must be `{ "code": "...", "language": "bash" }` (language optional).
    """
    steps = [step.to_debug_step() for step in body.steps]
    return await _run_debug(str(body.url), steps)


@router.post("/debug-run/code-block", response_model=DebugRunResponse)
async def debug_run_code_block(body: CodeBlockDebugRunRequest) -> DebugRunResponse:
    """
    Run a code block split into /interact steps via Claude.

    Supports node, python, or bash. Requires ANTHROPIC_API_KEY.
    Returns parsed_steps and step_summaries in the response.
    """
    try:
        split = await split_code_block(body.code_block, language=body.language)
    except AnthropicNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except CodeSplitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        exc_name = type(exc).__name__
        if exc_name in ("NotFoundError", "AuthenticationError", "PermissionDeniedError"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Anthropic API error ({exc_name}): {exc}. "
                    "Check ANTHROPIC_API_KEY and ANTHROPIC_MODEL "
                    "(default: claude-sonnet-4-6)."
                ),
            ) from exc
        raise

    lang = split.language.value
    steps = [DebugStep(code=step.code, language=lang) for step in split.steps]
    return await _run_debug(
        str(body.url),
        steps,
        parsed_steps=split.codes,
        step_summaries=split.summaries,
    )


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
