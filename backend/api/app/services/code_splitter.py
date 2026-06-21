"""Split Playwright/agent-browser code blocks into /interact steps via Claude."""

from __future__ import annotations

import os

from anthropic import AsyncAnthropic

from app.constants.code_splitter import USER_PROMPTS, system_prompt
from app.models.code_splitter import (
    AnthropicNotConfiguredError,
    CodeSplitError,
    CodeSplitPlan,
    CodeSplitResult,
)
from app.models.schemas import InteractLanguage
from app.services.code_split_result_builder import build_code_split_result


async def split_code_block(
    code_block: str,
    *,
    language: InteractLanguage = InteractLanguage.NODE,
) -> CodeSplitResult:
    """Split a multi-line script into ordered /interact steps using Claude.

    Sends the script to Claude with language-specific splitting instructions and
    parses the response as a structured plan. Each returned step is validated
    and formatted for isolated Firecrawl /interact execution (see
    ``build_code_split_result``).

    Args:
        code_block: Full Playwright or agent-browser script to split.
        language: Target runtime — node (default), python, or bash.

    Returns:
        Ordered steps with prepared code and human-readable summaries.

    Raises:
        CodeSplitError: If ``code_block`` is empty or Claude returns invalid output.
        AnthropicNotConfiguredError: If ``ANTHROPIC_API_KEY`` is not set.
    """
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
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt(language),
        messages=[
            {
                "role": "user",
                "content": f"{USER_PROMPTS[language]}\n\n{source}",
            }
        ],
        output_format=CodeSplitPlan,
    )

    plan = response.parsed_output
    if plan is None:
        raise CodeSplitError("Claude did not return structured code steps")

    return build_code_split_result(plan, language=language)
