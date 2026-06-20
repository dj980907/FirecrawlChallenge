"""Tests for debug step schemas."""

import pytest
from pydantic import ValidationError

from app.models.schemas import DebugRunRequest, DebugStep


def test_step_with_prompt() -> None:
    step = DebugStep(prompt="Click the login button")
    assert step.action_label() == "Click the login button"


def test_step_with_code() -> None:
    step = DebugStep(code="await page.click('#login'); true")
    assert "page.click" in step.action_label()


def test_step_requires_prompt_or_code() -> None:
    with pytest.raises(ValidationError):
        DebugStep()

    with pytest.raises(ValidationError):
        DebugStep(prompt="Do something", code="await page.click('x'); true")


def test_debug_run_request() -> None:
    body = DebugRunRequest(
        url="https://example.com",
        steps=[
            DebugStep(prompt="Wait for the page to load"),
            DebugStep(code="await page.title();"),
        ],
    )
    assert len(body.steps) == 2
