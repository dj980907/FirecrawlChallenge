"""Tests for debug step schemas."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    CodeBlockDebugRunRequest,
    DebugStep,
    InteractLanguage,
)


def test_code_block_debug_run_request() -> None:
    body = CodeBlockDebugRunRequest(
        url="https://example.com",
        code_block="await page.title(); true",
        language=InteractLanguage.NODE,
    )
    assert body.language == InteractLanguage.NODE


def test_internal_debug_step_requires_code() -> None:
    with pytest.raises(ValidationError):
        DebugStep(code="")


def test_debug_step_action_label() -> None:
    step = DebugStep(code="await page.click('#login'); true")
    assert "page.click" in step.action_label()


def test_debug_step_with_language() -> None:
    step = DebugStep(
        code="agent-browser click @e1\ntrue",
        language=InteractLanguage.BASH,
    )
    assert step.language == InteractLanguage.BASH
