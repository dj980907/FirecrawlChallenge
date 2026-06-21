"""Tests for API key auth on debug routes."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.helpers.auth import configured_api_key, require_api_key
from app.main import app

client = TestClient(app)

_MIN_ACTIONS_BODY = {
    "url": "https://example.com",
    "actions": [{"type": "wait", "milliseconds": 100}],
}


@pytest.mark.asyncio
async def test_require_api_key_skipped_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)
    assert configured_api_key() is None
    await require_api_key(api_key=None, credentials=None)


@pytest.mark.asyncio
async def test_require_api_key_rejects_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=None, credentials=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_accepts_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    await require_api_key(api_key="test-secret", credentials=None)


@pytest.mark.asyncio
async def test_require_api_key_accepts_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-secret")
    await require_api_key(api_key=None, credentials=credentials)


def test_debug_router_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    response = client.post("/debug/scrape/actions", json=_MIN_ACTIONS_BODY)
    assert response.status_code == 401


def test_health_stays_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    response = client.get("/health/")
    assert response.status_code == 200
