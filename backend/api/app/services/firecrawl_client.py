import os

from firecrawl import FirecrawlApp

_client: FirecrawlApp | None = None


def get_firecrawl_client() -> FirecrawlApp:
    global _client
    if _client is None:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is not set")
        _client = FirecrawlApp(api_key=api_key)
    return _client
