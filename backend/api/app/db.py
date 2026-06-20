import asyncio
import os
from functools import lru_cache

from supabase import Client, create_client


class SupabaseNotConfiguredError(RuntimeError):
    """Raised when Supabase env vars are missing."""


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SupabaseNotConfiguredError(f"{name} is not set")
    return value


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the service role key."""
    url = _require_env("SUPABASE_URL")
    key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


async def verify_supabase_connection() -> None:
    """Ping Supabase by selecting from extractors (empty result is fine)."""
    await asyncio.to_thread(_ping_supabase)


def _ping_supabase() -> None:
    client = get_supabase_client()
    client.table("extractors").select("id").limit(1).execute()
