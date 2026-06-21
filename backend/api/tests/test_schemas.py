"""Tests for debug step schemas."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    CodeDebugRunRequest,
    CodeDebugStep,
    DebugStep,
    InteractLanguage,
    MixedDebugRunRequest,
    MixedDebugStep,
    PromptDebugRunRequest,
    PromptDebugStep,
    normalize_interact_language,
)


def test_prompt_step() -> None:
    step = PromptDebugStep(prompt="Click the login button")
    assert step.to_debug_step().action_label() == "Click the login button"


def test_code_step() -> None:
    step = CodeDebugStep(code="await page.click('#login'); true")
    assert "page.click" in step.to_debug_step().action_label()


def test_mixed_step_requires_prompt_or_code() -> None:
    with pytest.raises(ValidationError):
        MixedDebugStep()

    with pytest.raises(ValidationError):
        MixedDebugStep(prompt="Do something", code="await page.click('x'); true")


def test_code_debug_run_request() -> None:
    body = CodeDebugRunRequest(
        url="https://example.com",
        steps=[CodeDebugStep(code="await page.title();")],
    )
    assert len(body.steps) == 1


def test_prompt_debug_run_request() -> None:
    body = PromptDebugRunRequest(
        url="https://example.com",
        steps=[PromptDebugStep(prompt="Wait for the page to load")],
    )
    assert len(body.steps) == 1


def test_mixed_debug_run_request() -> None:
    body = MixedDebugRunRequest(
        url="https://example.com",
        steps=[
            MixedDebugStep(prompt="Wait for the page to load"),
            MixedDebugStep(code="await page.title();"),
        ],
    )
    assert len(body.steps) == 2


def test_internal_debug_step_validation() -> None:
    with pytest.raises(ValidationError):
        DebugStep()


def test_normalize_interact_language() -> None:
    assert normalize_interact_language("py") == InteractLanguage.PYTHON
    assert normalize_interact_language("shell") == InteractLanguage.BASH
    assert normalize_interact_language(None) == InteractLanguage.NODE


def test_code_step_with_language() -> None:
    step = CodeDebugStep(code="agent-browser click @e1\ntrue", language=InteractLanguage.BASH)
    assert step.to_debug_step().language == "bash"
