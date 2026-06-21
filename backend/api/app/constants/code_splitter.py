"""Prompt constants for Claude code splitting."""

from app.models.schemas import InteractLanguage

BASE_SYSTEM_PROMPT = """You split scripts into separate steps for Firecrawl /interact code mode.

Critical rules:
- Each step is a separate /interact call with an isolated execution context. Only the browser DOM persists between steps — NOT variables from prior steps.
- Keep variable declarations in the SAME step as any later statement that uses those variables.
- Keep `if`/`try` blocks intact in a single step.
- Prefer one logical browser action per step when variables are not shared.
- Preserve selectors, element refs, and string literals exactly.
- Output only executable code — no markdown fences."""

LANGUAGE_SYSTEM_ADDONS: dict[InteractLanguage, str] = {
    InteractLanguage.NODE: """Language: Playwright JavaScript (Node).
- Use `await page...` for browser actions.
- Avoid `waitForLoadState("networkidle")` on heavy sites; prefer `domcontentloaded` plus `waitForTimeout`.""",
    InteractLanguage.PYTHON: """Language: Playwright Python async.
- The `page` object is pre-configured. Use `await page...`.
- Avoid `wait_for_load_state("networkidle")` on heavy sites; prefer `domcontentloaded` plus `wait_for_timeout`.""",
    InteractLanguage.BASH: """Language: agent-browser bash.
- Use commands such as snapshot, click @e1, fill @e1 "text", scroll, and screenshot.
- Keep commands that depend on prior shell variables in the SAME step.""",
}

USER_PROMPTS: dict[InteractLanguage, str] = {
    InteractLanguage.NODE: "Split this Playwright JavaScript script into /interact steps:",
    InteractLanguage.PYTHON: "Split this Playwright Python script into /interact steps:",
    InteractLanguage.BASH: "Split this agent-browser bash script into /interact steps:",
}


def system_prompt(language: InteractLanguage) -> str:
    return f"{BASE_SYSTEM_PROMPT}\n\n{LANGUAGE_SYSTEM_ADDONS[language]}"
