from fastapi import HTTPException, status

from app.controllers.debug_controller import run_debug
from app.models.schemas import CodeBlockDebugRunRequest, DebugRunResponse, DebugStep
from app.services.code_splitter import (
    AnthropicNotConfiguredError,
    CodeSplitError,
    split_code_block,
)


async def run_code_block_debug(body: CodeBlockDebugRunRequest) -> DebugRunResponse:
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

    steps = [DebugStep(code=step.code, language=split.language) for step in split.steps]
    return await run_debug(
        str(body.url),
        steps,
        parsed_steps=split.codes,
        step_summaries=split.summaries,
    )
