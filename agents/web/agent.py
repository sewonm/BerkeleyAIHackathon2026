"""
Web research agent.

Responsibility: scrape news, political, and cultural sources via Browserbase
and emit a ResearchOutput. No LLM reasoning here.

Run standalone:
    python agents/web/agent.py KXPRES-26NOV03 "Will X win the 2026 election?"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from schemas.schema import ResearchOutput, WebEvidence


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def scrape_web(market_title: str) -> dict:
    # TODO: replace with real Browserbase scrape
    # from browserbase import Browserbase
    # bb = Browserbase(api_key=os.getenv("BROWSERBASE_API_KEY"))
    # session = bb.sessions.create(project_id=os.getenv("BROWSERBASE_PROJECT_ID"))
    #
    # Build search queries from market_title, then scrape:
    #   Google News, Reuters, AP, Twitter/X, Reddit
    # Extract the most relevant headline + excerpt per source.
    return {
        "headline": f"Mock headline related to: {market_title}",
        "excerpt": "Mock excerpt: sentiment appears moderately positive based on recent coverage.",
        "source_name": "Reuters (mock)",
        "published_at": "2025-06-20T12:00:00Z",
        "raw_text": "Mock raw text from scrape. Replace with actual Browserbase page content.",
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_web_agent(market_id: str, market_title: str = "") -> ResearchOutput:
    try:
        scraped = scrape_web(market_title or market_id)
        data_quality = 0.0  # TODO: set to 1.0 once real Browserbase calls are wired in
    except Exception as e:
        return ResearchOutput(
            agent="web",
            market_id=market_id,
            applicable=False,
            evidence=WebEvidence(
                headline="unavailable",
                excerpt="",
                source_name="",
                raw_text=f"Scrape failed: {e}",
            ),
            data_quality=0.0,
            sources=[],
        )

    evidence = WebEvidence(
        headline=scraped["headline"],
        excerpt=scraped["excerpt"],
        source_name=scraped["source_name"],
        published_at=scraped.get("published_at"),
        raw_text=scraped["raw_text"],
    )

    return ResearchOutput(
        agent="web",
        market_id=market_id,
        applicable=True,
        evidence=evidence,
        data_quality=data_quality,
        sources=[scraped["source_name"]],
    )


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "KXPRES-26NOV03"
    market_title = sys.argv[2] if len(sys.argv) > 2 else ""
    print(run_web_agent(market_id, market_title).model_dump_json(indent=2))
