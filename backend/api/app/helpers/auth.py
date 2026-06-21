"""API key auth for public-facing debug endpoints."""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


def configured_api_key() -> str | None:
    value = os.getenv("API_KEY", "").strip()
    return value or None


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """Require a matching API key when the API_KEY env var is set."""
    expected = configured_api_key()
    if expected is None:
        return

    provided = api_key
    if credentials is not None and credentials.scheme.lower() == "bearer":
        provided = credentials.credentials

    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
