"""Split Playwright/agent-browser code blocks into /interact steps via Claude."""

from __future__ import annotations

import os

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from app.models.schemas import InteractLanguage, normalize_interact_language

SYSTEM_PROMPTS: dict[InteractLanguage, str] = {
    InteractLanguage.NODE: """You split Playwright JavaScript into separate steps for Firecrawl /interact code mode (Node).

Critical rules:
- Each step is a separate /interact call with an isolated JS context. Only the browser DOM persists between steps — NOT JavaScript variables.
- Keep `const`/`let`/`var` declarations in the SAME step as any later statement that uses those variables.
- Keep `if`/`try` blocks intact in a single step.
- Prefer one logical browser action per step when variables are not shared.
- Intermediate steps must be valid standalone code ending with `; true`.
- The final step may return data (e.g. JSON.stringify(...)) without appending `; true`.
- Avoid `waitForLoadState("networkidle")` on heavy sites; prefer `domcontentloaded` plus `waitForTimeout`.
- Preserve selectors and string literals exactly.
- Output only executable code — no markdown fences.""",
    InteractLanguage.PYTHON: """You split Playwright Python into separate steps for Firecrawl /interact code mode (Python async).

Critical rules:
- Each step is a separate /interact call with an isolated Python context. Only the browser DOM persists — NOT Python variables.
- Keep variable assignments in the SAME step as any later statement that uses those variables.
- Keep `if`/`try` blocks intact in a single step.
- The `page` object is pre-configured (Playwright async API). Use `await page...`.
- Intermediate steps must be valid standalone code whose last expression is `True`.
- The final step may return data (e.g. `json.dumps(...)`) without trailing `True`.
- Avoid `wait_for_load_state("networkidle")` on heavy sites; prefer `domcontentloaded` plus `wait_for_timeout`.
- Preserve selectors and string literals exactly.
- Output only executable Python — no markdown fences.""",
    InteractLanguage.BASH: """You split agent-browser bash commands into separate steps for Firecrawl /interact code mode.

Critical rules:
- Each step is a separate /interact call with an isolated shell context. Only the browser DOM persists — NOT shell variables.
- Use `agent-browser` commands: snapshot, click @e1, fill @e1 "text", scroll, screenshot, etc.
- Keep related commands that depend on prior shell variables in the SAME step.
- Prefer one logical browser action per step when possible.
- Intermediate steps must end with a line `true` so the step succeeds.
- The final step may print or return output without a trailing `true`.
- Preserve element refs and selectors exactly.
- Output only executable bash — no markdown fences.""",
}

USER_PROMPTS: dict[InteractLanguage, str] = {
    InteractLanguage.NODE: "Split this Playwright JavaScript script into /interact steps:",
    InteractLanguage.PYTHON: "Split this Playwright Python script into /interact steps:",
    InteractLanguage.BASH: "Split this agent-browser bash script into /interact steps:",
}


class CodeSplitError(ValueError):
    """Raised when a code block cannot be split."""


class CodeSplitStepOut(BaseModel):
    code: str = Field(
        description="Standalone code executed in one /interact call",
    )
    summary: str = Field(
        description="Short human-readable label for this step (shown in debug reports)",
        max_length=120,
    )


class CodeSplitPlan(BaseModel):
    steps: list[CodeSplitStepOut] = Field(
        min_length=1,
        description="Ordered list of /interact code steps",
    )


class CodeSplitStep(BaseModel):
    code: str = Field(description="Prepared code for one /interact call")
    summary: str = Field(description="Human-readable label for this step")


class CodeSplitResult(BaseModel):
    language: InteractLanguage
    steps: list[CodeSplitStep] = Field(
        min_length=1,
        description="Ordered steps ready to run via /interact",
    )

    @property
    def codes(self) -> list[str]:
        return [step.code for step in self.steps]

    @property
    def summaries(self) -> list[str]:
        return [step.summary for step in self.steps]


class AnthropicNotConfiguredError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is not set."""


def prepare_step_code(
    code: str,
    *,
    language: InteractLanguage,
    is_last: bool,
) -> str:
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


def _anthropic_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _build_result(plan: CodeSplitPlan, *, language: InteractLanguage) -> CodeSplitResult:
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


async def split_code_block(
    code_block: str,
    *,
    language: InteractLanguage | str | None = None,
) -> CodeSplitResult:
    """Use Claude structured output to split a code block for /interact."""
    resolved = normalize_interact_language(language)
    source = code_block.strip()
    if not source:
        raise CodeSplitError("code_block is empty")

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise AnthropicNotConfiguredError(
            "ANTHROPIC_API_KEY is not set. "
            "Create an API key at https://console.anthropic.com/ "
            "(separate from a claude.ai subscription)."
        )

    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.parse(
        model=_anthropic_model(),
        max_tokens=4096,
        system=SYSTEM_PROMPTS[resolved],
        messages=[
            {
                "role": "user",
                "content": f"{USER_PROMPTS[resolved]}\n\n{source}",
            }
        ],
        output_format=CodeSplitPlan,
    )

    plan = response.parsed_output
    if plan is None:
        raise CodeSplitError("Claude did not return structured code steps")

    return _build_result(plan, language=resolved)
