from fastapi import APIRouter

from app.controllers.code_block_debug_controller import run_code_block_debug
from app.models.schemas import CodeBlockDebugRunRequest, DebugRunResponse

router = APIRouter()


@router.post("/debug-run/code-block", response_model=DebugRunResponse)
async def debug_run_code_block(body: CodeBlockDebugRunRequest) -> DebugRunResponse:
    """
    Run a code block split into /interact steps via Claude.

    Supports node, python, or bash. Requires ANTHROPIC_API_KEY.
    Returns parsed_steps and step_summaries in the response.
    """
    return await run_code_block_debug(body)
