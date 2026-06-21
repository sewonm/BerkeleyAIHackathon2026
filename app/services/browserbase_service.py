"""
Browserbase web research service.

REAL API (confirmed from docs.browserbase.com):

  Step 1 — Search:  bb.search.web(query, num_results=5)
                    -> returns list of {url, title} (no browser, cheap)

  Step 2 — Fetch:   bb.fetch_api.create(url, format="markdown")
                    -> returns page content as clean markdown (no browser, cheap)

  Step 3 — Browser: bb.sessions.create() + playwright CDP connect
                    -> only needed for interactive/JS-heavy pages (skip for now)

For our web research agent, steps 1+2 are enough.

INSTALL:
  pip install browserbase>=1.11.0

ENV VARS:
  BROWSERBASE_API_KEY   (required)
  BROWSERBASE_PROJECT_ID (optional)
"""

import os
import json

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")


def search_and_fetch(query: str, max_results: int = 5) -> list[dict]:
    """
    Main entry point. Search -> Fetch -> return raw chunks for compressor.

    Returns:
        list of dicts: [{"source_name": str, "url": str, "raw_text": str, "raw_tokens": int}]
    """
    if not BROWSERBASE_API_KEY:
        print("[browserbase] No API key — using mock data")
        return _mock_web_results(query)

    try:
        return _live_search_and_fetch(query, max_results)
    except Exception as e:
        print(f"[browserbase] Error: {e} — falling back to mock")
        return _mock_web_results(query)


def _live_search_and_fetch(query: str, max_results: int) -> list[dict]:
    from browserbase import Browserbase

    bb = Browserbase(api_key=BROWSERBASE_API_KEY)

    # Step 1: Search — returns titles + URLs, no browser needed
    search_response = bb.search.web(query=query, num_results=max_results)

    results = []

    # Step 2: Fetch each URL as clean markdown
    for result in search_response.results:
        try:
            fetch_response = bb.fetch_api.create(url=result.url, format="markdown")
            text = fetch_response.content[:4000]
            results.append({
                "source_name": result.title,
                "url": result.url,
                "raw_text": text,
                "raw_tokens": len(text.split()),
            })
        except Exception as e:
            print(f"[browserbase] Skipping {result.url}: {e}")

    return results


def _mock_web_results(query: str) -> list[dict]:
    mock_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "examples", "raw_context", "sample_web_evidence.json"
    )
    if os.path.exists(mock_path):
        with open(mock_path) as f:
            return json.load(f).get("chunks", [])

    return [{
        "source_name": "Mock",
        "url": "https://example.com",
        "raw_text": f"Mock result for: {query}. Set BROWSERBASE_API_KEY.",
        "raw_tokens": 15,
    }]
