"""
Browserbase web research service.

Uses Browserbase Sessions + Stagehand to search the web, fetch pages,
and return raw text chunks. The web agent converts these chunks into claims.

SETUP:
  pip install browserbase stagehand-py playwright
  playwright install chromium

DOCS TO CHECK:
  https://docs.browserbase.com/quickstart/python
  https://docs.browserbase.com/reference/api/create-a-session
  https://stagehand.dev/docs/python

ENV VARS REQUIRED:
  BROWSERBASE_API_KEY
  BROWSERBASE_PROJECT_ID
"""

import os
import json
from typing import Optional

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")


def search_and_fetch(query: str, max_results: int = 5) -> list[dict]:
    """
    Main entry point for the web research agent.

    1. Uses Browserbase to open a browser session
    2. Searches Google for the query
    3. Fetches and extracts text from top result pages
    4. Returns list of raw text chunks for the compressor

    Returns:
        list of dicts: [{"source_name": str, "url": str, "raw_text": str, "raw_tokens": int}]
    """
    if not BROWSERBASE_API_KEY:
        print("BROWSERBASE_API_KEY not set — returning mock data")
        return _mock_web_results(query)

    try:
        return _live_browserbase_search(query, max_results)
    except Exception as e:
        print(f"Browserbase error: {e} — falling back to mock data")
        return _mock_web_results(query)


def _live_browserbase_search(query: str, max_results: int) -> list[dict]:
    """
    Real Browserbase implementation.

    CHECK DOCS before editing:
    - Session creation: https://docs.browserbase.com/reference/api/create-a-session
    - Playwright connect: https://docs.browserbase.com/quickstart/python
    - Stagehand extraction: https://stagehand.dev/docs/python/reference/act-extract
    """
    from browserbase import Browserbase
    from playwright.sync_api import sync_playwright

    bb = Browserbase(api_key=BROWSERBASE_API_KEY)
    session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        context = browser.contexts[0]
        page = context.pages[0]

        # Step 1: Search Google
        page.goto(f"https://www.google.com/search?q={query}")
        page.wait_for_load_state("networkidle")

        # Step 2: Extract top result URLs
        # CHECK DOCS: exact selector may vary — verify with Stagehand or Playwright inspector
        links = page.eval_on_selector_all(
            "a[href*='http']",
            "els => els.map(e => ({href: e.href, text: e.innerText})).slice(0, 10)"
        )

        result_urls = [
            l["href"] for l in links
            if "google.com" not in l["href"] and l["href"].startswith("http")
        ][:max_results]

        # Step 3: Fetch each page and extract text
        for url in result_urls:
            try:
                page.goto(url, timeout=8000)
                page.wait_for_load_state("domcontentloaded")
                text = page.inner_text("body")[:3000]  # cap at 3k chars per page
                raw_tokens = len(text.split())
                results.append({
                    "source_name": page.title(),
                    "url": url,
                    "raw_text": text,
                    "raw_tokens": raw_tokens
                })
            except Exception:
                continue

        browser.close()

    return results


def _mock_web_results(query: str) -> list[dict]:
    """
    Fallback: loads sample web evidence from demo_data.
    Used when BROWSERBASE_API_KEY is not set or call fails.
    """
    mock_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "examples", "raw_context", "sample_web_evidence.json"
    )
    if os.path.exists(mock_path):
        with open(mock_path) as f:
            data = json.load(f)
            return data.get("chunks", [])

    # Hardcoded fallback if file missing
    return [
        {
            "source_name": "Mock ESPN - Injury Report",
            "url": "https://espn.com/mock",
            "raw_text": f"Mock web result for query: {query}. No real data — set BROWSERBASE_API_KEY.",
            "raw_tokens": 50
        }
    ]
