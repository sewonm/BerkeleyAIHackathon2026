"""Browserbase service — web search + markdown fetch, with mock fallback.

ENV VARS:
    BROWSERBASE_API_KEY   — Browserbase API key (enables fetch_api)
    SERPER_API_KEY        — Serper.dev key for web search (preferred)
"""

import os
import httpx
from typing import Optional

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

_bb_client = None


def _get_bb():
    global _bb_client
    if _bb_client is None and BROWSERBASE_API_KEY:
        try:
            from browserbase import Browserbase
            _bb_client = Browserbase(api_key=BROWSERBASE_API_KEY)
        except Exception:
            pass
    return _bb_client


class BrowserbaseService:
    """Web search + markdown page fetch.

    Priority:
      search  → Serper API → Browserbase search.web → mock
      fetch   → Browserbase fetch_api → plain httpx → mock
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or BROWSERBASE_API_KEY
        if self.api_key and _get_bb() is None:
            try:
                from browserbase import Browserbase
                global _bb_client
                _bb_client = Browserbase(api_key=self.api_key)
            except Exception:
                pass

    async def search_web(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web. Returns list of {url, title, snippet}."""
        if SERPER_API_KEY:
            try:
                return await self._serper_search(query, max_results)
            except Exception:
                pass
        bb = _get_bb()
        if bb is not None:
            try:
                results = bb.search.web(query=query)
                return [
                    {
                        "url": r.url,
                        "title": getattr(r, "title", ""),
                        "snippet": getattr(r, "snippet", ""),
                    }
                    for r in (getattr(results, "results", None) or [])[:max_results]
                ]
            except Exception:
                pass
        return self._mock_search(query)

    async def fetch_as_markdown(self, url: str) -> str:
        """Fetch a URL and return content as markdown."""
        bb = _get_bb()
        if bb is not None:
            try:
                result = bb.fetch_api.create(url=url, format="markdown")
                return result.content or ""
            except Exception:
                pass
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                return r.text[:5000]
        except Exception:
            return self._mock_fetch(url)

    async def _serper_search(self, query: str, max_results: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("organic", [])[:max_results]
        ]

    def _mock_search(self, query: str) -> list[dict]:
        return [
            {
                "url": "https://example.com/mock",
                "title": f"Mock result: {query}",
                "snippet": f"Mock search result for query: {query}",
            }
        ]

    def _mock_fetch(self, url: str) -> str:
        return f"# Mock Content\n\nMock fetch from: {url}\n"
