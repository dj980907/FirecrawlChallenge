"""Convert Claude split plans into /interact-ready code steps."""

from app.models.code_splitter import (
    CodeSplitError,
    CodeSplitPlan,
    CodeSplitResult,
    CodeSplitStep,
)
from app.models.schemas import InteractLanguage


def prepare_step_code(
    code: str,
    *,
    language: InteractLanguage,
    is_last: bool,
) -> str:
    """Format one step's code for a standalone /interact call."""
    stmt = code.strip()
    if not stmt:
        raise CodeSplitError("Empty statement after split")
    if is_last:
        return stmt

    if language == InteractLanguage.NODE:
        stmt = stmt.rstrip(";")
        return f"{stmt}; true"

    if language == InteractLanguage.PYTHON:
        return f"{stmt}\nTrue"

    return f"{stmt}\ntrue"


def build_code_split_result(
    plan: CodeSplitPlan,
    *,
    language: InteractLanguage,
) -> CodeSplitResult:
    """Turn Claude's structured split plan into steps ready for /interact.

    Claude returns raw code snippets per step. Before running them through
    Firecrawl /interact, each step must be validated and formatted for isolated
    execution (only the browser DOM persists between calls).

    This function:
    - Rejects empty plans or steps with blank code.
    - Appends language-specific success sentinels to intermediate steps
      (e.g. ``; true`` for Node, ``True`` for Python, ``true`` for bash) so
      each /interact call succeeds on its own.
    - Leaves the final step unchanged so it can return data to the caller.
    - Normalizes step summaries for debug reports, falling back to the first
      line of code when Claude omits a summary.

    Args:
        plan: Structured output from Claude (ordered steps with code + summary).
        language: Target /interact language (node, python, or bash).

    Returns:
        Validated steps prepared for sequential /interact execution.

    Raises:
        CodeSplitError: If the plan is empty or any step has no code.
    """
    if not plan.steps:
        raise CodeSplitError("Claude returned no steps")

    last_index = len(plan.steps) - 1
    result_steps: list[CodeSplitStep] = []

    for index, step in enumerate(plan.steps):
        code = step.code.strip()
        if not code:
            raise CodeSplitError(f"Step {index + 1} has empty code")
        result_steps.append(
            CodeSplitStep(
                code=prepare_step_code(code, language=language, is_last=index == last_index),
                summary=step.summary.strip() or code.splitlines()[0][:120],
            )
        )

    return CodeSplitResult(language=language, steps=result_steps)
