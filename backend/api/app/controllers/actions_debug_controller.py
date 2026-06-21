from fastapi import HTTPException, status

from app.controllers.debug_controller import run_debug
from app.models.action_compiler import ActionsCompileError
from app.models.schemas import DebugRunResponse, DebugStep
from app.models.scrape_actions import ActionsDebugRunRequest
from app.services.actions_compiler import compile_actions


async def run_actions_debug(body: ActionsDebugRunRequest) -> DebugRunResponse:
    try:
        compiled = compile_actions(body.actions, language=body.language)
    except ActionsCompileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    steps = [
        DebugStep(code=step.code, language=compiled.language) for step in compiled.steps
    ]
    return await run_debug(
        str(body.url),
        steps,
        parsed_steps=compiled.codes,
        step_summaries=compiled.summaries,
    )
