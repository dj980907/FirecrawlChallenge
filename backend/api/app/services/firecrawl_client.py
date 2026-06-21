import os
from functools import lru_cache
from typing import Any
from firecrawl import Firecrawl


class FirecrawlNotConfiguredError(RuntimeError):
    """Raised when FIRECRAWL_API_KEY is not set."""


@lru_cache
def get_firecrawl_client() -> Any:

    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise FirecrawlNotConfiguredError("FIRECRAWL_API_KEY is not set")
    return Firecrawl(api_key=api_key)
