"""Politics/news research agent — scrapes news sources via Browserbase."""

import os
from datetime import datetime, timezone
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk

_BROWSERBASE_AVAILABLE = bool(os.getenv("BROWSERBASE_API_KEY"))


class PoliticsNewsAgent(BaseAgent):
    """
    Scrapes news, political, and cultural sources via Browserbase and returns
    raw EvidenceChunks for the compression agent.

    No LLM reasoning here — raw data only.

    Requires env vars:
        BROWSERBASE_API_KEY    — from https://browserbase.com
        BROWSERBASE_PROJECT_ID — your Browserbase project ID
    Falls back to mock data if not set.
    """

    def __init__(self):
        super().__init__(
            name="PoliticsNewsAgent",
            description="Scrapes news and political sources via Browserbase for a given market"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        now = datetime.now(timezone.utc).isoformat()

        if not _BROWSERBASE_AVAILABLE:
            return self._mock_evidence(market, now)

        try:
            scraped = self._scrape(market)
        except Exception as e:
            print(f"[{self.name}] Scrape error: {e}")
            return []

        return [self._to_chunk(item, now) for item in scraped]

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _scrape(self, market: Market) -> list[dict]:
        # TODO: replace with real Browserbase scrape
        # from browserbase import Browserbase
        # bb = Browserbase(api_key=os.getenv("BROWSERBASE_API_KEY"))
        # session = bb.sessions.create(project_id=os.getenv("BROWSERBASE_PROJECT_ID"))
        #
        # Build search queries from market.title / market.question, then scrape:
        #   - Google News: f"https://news.google.com/search?q={query}"
        #   - Reuters:     "https://www.reuters.com"
        #   - AP News:     "https://apnews.com"
        #   - Politico:    "https://www.politico.com" (for politics markets)
        #
        # For each page:
        #   page_text = session.get_page_text(url)
        #   Extract the most relevant headline + excerpt
        #   Append {"headline": ..., "excerpt": ..., "source": ..., "url": ...}
        raise NotImplementedError("Set BROWSERBASE_API_KEY and implement _scrape")

    # ------------------------------------------------------------------
    # EvidenceChunk builder
    # ------------------------------------------------------------------

    def _to_chunk(self, item: dict, now: str) -> EvidenceChunk:
        text = (
            f"Source: {item.get('source', 'unknown')}\n"
            f"Headline: {item.get('headline', '')}\n"
            f"Excerpt: {item.get('excerpt', '')}\n"
        )
        return EvidenceChunk(
            source_type="politics_news",
            text=text,
            source_url=item.get("url"),
            timestamp=item.get("published_at", now),
            confidence=0.8,
            metadata={"source": item.get("source"), "agent": self.name},
        )

    # ------------------------------------------------------------------
    # Mock fallback
    # ------------------------------------------------------------------

    def _mock_evidence(self, market: Market, now: str) -> List[EvidenceChunk]:
        print(f"[{self.name}] BROWSERBASE_API_KEY not set — returning mock evidence")
        return [
            EvidenceChunk(
                source_type="politics_news",
                text=(
                    f"Source: Reuters (MOCK)\n"
                    f"Headline: Mock headline related to: {market.title}\n"
                    f"Excerpt: Mock excerpt — sentiment appears moderately positive "
                    f"based on recent coverage of {market.question}\n"
                ),
                source_url=None,
                timestamp=now,
                confidence=0.0,
                metadata={"mock": True},
            ),
        ]
