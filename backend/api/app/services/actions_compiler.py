"""Compile Firecrawl scrape actions[] into /interact code steps."""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic import TypeAdapter

from app.models.action_compiler import (
    ActionCompileResult,
    ActionCompileStep,
    ActionsCompileError,
)
from app.models.schemas import InteractLanguage
from app.models.scrape_actions import (
    ClickAction,
    ExecuteJavascriptAction,
    FirecrawlAction,
    PDFAction,
    PressAction,
    ScrapeCaptureAction,
    ScreenshotAction,
    ScrollAction,
    WaitAction,
    WriteAction,
)
from app.services.code_split_result_builder import prepare_step_code

_action_adapter = TypeAdapter(FirecrawlAction)


def _truncate(text: str, limit: int = 80) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def _compile_wait(action: WaitAction, language: InteractLanguage) -> tuple[str, str]:
    if action.milliseconds is not None and action.selector:
        raise ActionsCompileError(
            "wait action cannot specify both milliseconds and selector"
        )

    if action.milliseconds is not None:
        summary = f"wait {action.milliseconds}ms"
        if language == InteractLanguage.NODE:
            return f"await page.waitForTimeout({action.milliseconds});", summary
        if language == InteractLanguage.PYTHON:
            return f"await page.wait_for_timeout({action.milliseconds})", summary
        return f"agent-browser wait {action.milliseconds}", summary

    if action.selector:
        selector = json.dumps(action.selector)
        summary = f"wait for {action.selector}"
        if language == InteractLanguage.NODE:
            return f"await page.waitForSelector({selector});", summary
        if language == InteractLanguage.PYTHON:
            return f"await page.wait_for_selector({selector})", summary
        return (
            f'agent-browser eval "await new Promise(r => {{ const el = document.querySelector({selector}); if (!el) throw new Error(\'selector not found\'); new MutationObserver(() => r()).observe(el, {{ attributes: true, childList: true, subtree: true }}); setTimeout(r, 30000); }}"',
            summary,
        )

    raise ActionsCompileError("wait action requires milliseconds or selector")


def _compile_click(action: ClickAction, language: InteractLanguage) -> tuple[str, str]:
    selector = json.dumps(action.selector)
    summary = f"click {action.selector}"
    if language == InteractLanguage.NODE:
        return f"await page.click({selector});", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.click({selector})", summary
    return (
        f"agent-browser eval \"document.querySelector({selector})?.click()\"",
        summary,
    )


def _compile_write(action: WriteAction, language: InteractLanguage) -> tuple[str, str]:
    text = json.dumps(action.text)
    summary = f"type {action.text!r}"
    if language == InteractLanguage.NODE:
        return f"await page.keyboard.type({text});", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.keyboard.type({text})", summary
    return f"agent-browser eval \"document.activeElement?.insertAdjacentText('beforeend', {text})\"", summary


def _compile_press(action: PressAction, language: InteractLanguage) -> tuple[str, str]:
    key = json.dumps(action.key)
    summary = f"press {action.key}"
    if language == InteractLanguage.NODE:
        return f"await page.keyboard.press({key});", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.keyboard.press({key})", summary
    return f"agent-browser eval \"document.activeElement?.dispatchEvent(new KeyboardEvent('keydown', {{ key: {key} }}))\"", summary


def _compile_scroll(action: ScrollAction, language: InteractLanguage) -> tuple[str, str]:
    delta = "window.innerHeight" if action.direction == "down" else "-window.innerHeight"
    summary = f"scroll {action.direction}"
    if action.selector:
        selector = json.dumps(action.selector)
        summary = f"scroll {action.direction} {action.selector}"
        if language == InteractLanguage.NODE:
            return f"await page.locator({selector}).scrollIntoViewIfNeeded();", summary
        if language == InteractLanguage.PYTHON:
            return f"await page.locator({selector}).scroll_into_view_if_needed()", summary
        return (
            f"agent-browser eval \"document.querySelector({selector})?.scrollIntoView()\"",
            summary,
        )

    if language == InteractLanguage.NODE:
        return f"await page.evaluate(() => window.scrollBy(0, {delta}));", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.evaluate('() => window.scrollBy(0, {delta})')", summary
    direction_flag = "down" if action.direction == "down" else "up"
    return f"agent-browser scroll {direction_flag}", summary


def _compile_scrape_capture(
    action: ScrapeCaptureAction,
    language: InteractLanguage,
) -> tuple[str, str]:
    summary = "scrape snapshot"
    if language == InteractLanguage.NODE:
        return (
            "JSON.stringify({ url: page.url(), title: await page.title() });",
            summary,
        )
    if language == InteractLanguage.PYTHON:
        return (
            "import json\n"
            "print(json.dumps({'url': page.url, 'title': await page.title()}))",
            summary,
        )
    return (
        'agent-browser eval "JSON.stringify({ url: location.href, title: document.title })"',
        summary,
    )


def _compile_execute_javascript(
    action: ExecuteJavascriptAction,
    language: InteractLanguage,
) -> tuple[str, str]:
    script = json.dumps(action.script)
    summary = f"executeJavascript: {_truncate(action.script)}"
    if language == InteractLanguage.NODE:
        return f"await page.evaluate((s) => {{ eval(s); }}, {script});", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.evaluate('(s) => eval(s)', {script})", summary
    return f"agent-browser eval {script}", summary


def _compile_screenshot(
    action: ScreenshotAction,
    language: InteractLanguage,
) -> tuple[str, str]:
    summary = "screenshot"
    full_page = action.full_page or False
    if language == InteractLanguage.NODE:
        return f"await page.screenshot({{ fullPage: {str(full_page).lower()} }});", summary
    if language == InteractLanguage.PYTHON:
        return f"await page.screenshot(full_page={full_page})", summary
    return "agent-browser screenshot", summary


def _compile_pdf(action: PDFAction, language: InteractLanguage) -> tuple[str, str]:
    raise ActionsCompileError(
        "pdf actions cannot be compiled to /interact steps; remove or replace this action"
    )


def _compile_single(action: FirecrawlAction, language: InteractLanguage) -> tuple[str, str]:
    if isinstance(action, WaitAction):
        return _compile_wait(action, language)
    if isinstance(action, ClickAction):
        return _compile_click(action, language)
    if isinstance(action, WriteAction):
        return _compile_write(action, language)
    if isinstance(action, PressAction):
        return _compile_press(action, language)
    if isinstance(action, ScrollAction):
        return _compile_scroll(action, language)
    if isinstance(action, ScrapeCaptureAction):
        return _compile_scrape_capture(action, language)
    if isinstance(action, ExecuteJavascriptAction):
        return _compile_execute_javascript(action, language)
    if isinstance(action, ScreenshotAction):
        return _compile_screenshot(action, language)
    if isinstance(action, PDFAction):
        return _compile_pdf(action, language)


def _parse_action(action: FirecrawlAction | dict[str, object]) -> FirecrawlAction:
    if isinstance(
        action,
        (
            WaitAction,
            ClickAction,
            WriteAction,
            PressAction,
            ScrollAction,
            ScrapeCaptureAction,
            ExecuteJavascriptAction,
            ScreenshotAction,
            PDFAction,
        ),
    ):
        return action
    return _action_adapter.validate_python(action)


def compile_actions(
    actions: Sequence[FirecrawlAction | dict[str, object]],
    *,
    language: InteractLanguage,
) -> ActionCompileResult:
    """Turn a Firecrawl scrape actions array into /interact-ready steps."""
    if not actions:
        raise ActionsCompileError("actions array is empty")

    last_index = len(actions) - 1
    compiled_steps: list[ActionCompileStep] = []

    for index, raw_action in enumerate(actions):
        action = _parse_action(raw_action)
        raw_code, summary = _compile_single(action, language)
        compiled_steps.append(
            ActionCompileStep(
                code=prepare_step_code(
                    raw_code,
                    language=language,
                    is_last=index == last_index,
                ),
                summary=summary,
            )
        )

    return ActionCompileResult(language=language, steps=compiled_steps)
