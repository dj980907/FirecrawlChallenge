"""Tests for scrape actions → /interact compilation."""

import pytest
from pydantic import ValidationError

from app.models.schemas import InteractLanguage
from app.models.scrape_actions import ActionsDebugRunRequest
from app.services.actions_compiler import ActionsCompileError, compile_actions


def test_actions_debug_run_request() -> None:
    body = ActionsDebugRunRequest(
        url="https://news.ycombinator.com",
        actions=[
            {"type": "wait", "milliseconds": 1000},
            {"type": "click", "selector": "a[href=\"newest\"]"},
        ],
    )
    assert body.language == InteractLanguage.NODE
    assert len(body.actions) == 2


def test_rejects_empty_actions() -> None:
    with pytest.raises(ValidationError):
        ActionsDebugRunRequest(
            url="https://example.com",
            actions=[],
        )


def test_compile_hn_workflow_node() -> None:
    result = compile_actions(
        [
            {"type": "wait", "milliseconds": 500},
            {"type": "click", "selector": 'a[href="newest"]'},
            {"type": "wait", "selector": ".titleline a"},
            {"type": "click", "selector": ".titleline a"},
            {
                "type": "executeJavascript",
                "script": "JSON.stringify({ title: document.title, url: location.href })",
            },
        ],
        language=InteractLanguage.NODE,
    )

    assert len(result.steps) == 5
    assert result.codes[0].endswith("; true")
    assert 'page.click("a[href=\\"newest\\"]")' in result.codes[1]
    assert "page.waitForSelector" in result.codes[2]
    assert "eval(s)" in result.codes[4]
    assert "executeJavascript" in result.summaries[4]


def test_compile_click_python() -> None:
    result = compile_actions(
        [{"type": "click", "selector": "#login"}],
        language=InteractLanguage.PYTHON,
    )
    assert result.codes[0] == "await page.click(\"#login\")"
    assert result.summaries[0] == "click #login"


def test_compile_write_bash() -> None:
    result = compile_actions(
        [{"type": "write", "text": "user@example.com"}],
        language=InteractLanguage.BASH,
    )
    assert "user@example.com" in result.codes[0]
    assert result.summaries[0] == "type 'user@example.com'"


def test_compile_scroll_down() -> None:
    result = compile_actions(
        [{"type": "scroll", "direction": "down"}],
        language=InteractLanguage.NODE,
    )
    assert "scrollBy" in result.codes[0]


def test_compile_rejects_wait_with_both_fields() -> None:
    with pytest.raises(ActionsCompileError, match="both milliseconds and selector"):
        compile_actions(
            [{"type": "wait", "milliseconds": 1000, "selector": "#x"}],
            language=InteractLanguage.NODE,
        )


def test_compile_rejects_pdf() -> None:
    with pytest.raises(ActionsCompileError, match="pdf actions"):
        compile_actions(
            [{"type": "pdf"}],
            language=InteractLanguage.NODE,
        )


def test_compile_rejects_empty_actions_list() -> None:
    with pytest.raises(ActionsCompileError, match="empty"):
        compile_actions([], language=InteractLanguage.NODE)


def test_compile_write_without_selector() -> None:
    result = compile_actions(
        [{"type": "write", "text": "hello"}],
        language=InteractLanguage.NODE,
    )
    assert "keyboard.type" in result.codes[0]
