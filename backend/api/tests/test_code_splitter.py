"""Tests for code splitting (mocked Claude responses)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import InteractLanguage
from app.services.code_splitter import (
    AnthropicNotConfiguredError,
    CodeSplitError,
    CodeSplitPlan,
    CodeSplitStepOut,
    prepare_step_code,
    split_code_block,
)


def _mock_parse_response(steps: list[CodeSplitStepOut]) -> MagicMock:
    response = MagicMock()
    response.parsed_output = CodeSplitPlan(steps=steps)
    return response


@pytest.mark.asyncio
async def test_split_code_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.parse = AsyncMock(
        return_value=_mock_parse_response(
            [
                CodeSplitStepOut(
                    code="await page.click('#login');",
                    summary="Click login",
                ),
                CodeSplitStepOut(
                    code="JSON.stringify({ ok: true });",
                    summary="Return result",
                ),
            ]
        )
    )

    with patch("app.services.code_splitter.AsyncAnthropic", return_value=mock_client):
        result = await split_code_block(
            "await page.click('#login');\nJSON.stringify({ ok: true });"
        )

    assert len(result.steps) == 2
    assert result.codes[0].endswith("true")
    assert "JSON.stringify" in result.codes[1]
    assert result.summaries == ["Click login", "Return result"]
    assert result.language == InteractLanguage.NODE

    mock_client.messages.parse.assert_awaited_once()
    call_kwargs = mock_client.messages.parse.await_args.kwargs
    assert call_kwargs["output_format"] is CodeSplitPlan


def test_prepare_step_code_node() -> None:
    assert prepare_step_code("await page.click('x')", language=InteractLanguage.NODE, is_last=False) == "await page.click('x'); true"
    assert prepare_step_code("return 1", language=InteractLanguage.NODE, is_last=True) == "return 1"


def test_prepare_step_code_python() -> None:
    assert prepare_step_code("await page.click('x')", language=InteractLanguage.PYTHON, is_last=False) == "await page.click('x')\nTrue"
    assert prepare_step_code("json.dumps({})", language=InteractLanguage.PYTHON, is_last=True) == "json.dumps({})"


def test_prepare_step_code_bash() -> None:
    assert prepare_step_code("agent-browser click @e1", language=InteractLanguage.BASH, is_last=False) == "agent-browser click @e1\ntrue"
    assert prepare_step_code("agent-browser scrape", language=InteractLanguage.BASH, is_last=True) == "agent-browser scrape"


@pytest.mark.asyncio
async def test_split_code_block_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.parse = AsyncMock(
        return_value=_mock_parse_response(
            [
                CodeSplitStepOut(code="await page.click('#login')", summary="Click login"),
                CodeSplitStepOut(code="json.dumps({'ok': True})", summary="Return result"),
            ]
        )
    )

    with patch("app.services.code_splitter.AsyncAnthropic", return_value=mock_client):
        result = await split_code_block("await page.click('#login')\njson.dumps({'ok': True})", language="python")

    assert result.language == InteractLanguage.PYTHON
    assert result.codes[0].endswith("True")
    assert "json.dumps" in result.codes[1]


@pytest.mark.asyncio
async def test_split_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AnthropicNotConfiguredError):
        await split_code_block("await page.click('x');")


@pytest.mark.asyncio
async def test_split_rejects_empty_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(CodeSplitError):
        await split_code_block("   ")


@pytest.mark.asyncio
async def test_split_rejects_missing_parsed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.parse = AsyncMock(return_value=MagicMock(parsed_output=None))

    with patch("app.services.code_splitter.AsyncAnthropic", return_value=mock_client):
        with pytest.raises(CodeSplitError, match="structured code steps"):
            await split_code_block("await page.click('x');")
