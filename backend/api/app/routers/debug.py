from fastapi import APIRouter

from app.controllers.actions_debug_controller import run_actions_debug
from app.controllers.code_block_debug_controller import run_code_block_debug
from app.models.schemas import CodeBlockDebugRunRequest, DebugRunResponse
from app.models.scrape_actions import ActionsDebugRunRequest

router = APIRouter()


@router.post("/scrape/actions", response_model=DebugRunResponse)
async def debug_run_scrape_actions(body: ActionsDebugRunRequest) -> DebugRunResponse:
    """
    Debug a Firecrawl scrape ``actions`` array step-by-step.

    Each action is compiled to an isolated /interact call (node, python, or bash).
    Returns the same debug report shape as ``/debug/interact/code``.
    """
    return await run_actions_debug(body)


@router.post("/interact/code", response_model=DebugRunResponse)
async def debug_run_code_block(body: CodeBlockDebugRunRequest) -> DebugRunResponse:
    """
    Run a code block split into /interact steps via Claude.

    Supports node, python, or bash. Requires ANTHROPIC_API_KEY.
    Returns parsed_steps and step_summaries in the response.
    """
    return await run_code_block_debug(body)
