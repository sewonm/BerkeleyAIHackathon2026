"""Sports research agent — fetches live odds, line movement, and injury data."""

import os
from datetime import datetime, timezone
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk

_ODDS_AVAILABLE = bool(os.getenv("ODDS_API_KEY"))


class SportsVideoAgent(BaseAgent):
    """
    Fetches live odds, line movement, and injury notes for a sports event
    and returns raw EvidenceChunks for the compression agent.

    No LLM reasoning here — raw data only.

    Requires env vars:
        ODDS_API_KEY  — TheOddsAPI key (https://the-odds-api.com/)
    Falls back to mock data if not set.
    """

    def __init__(self):
        super().__init__(
            name="SportsVideoAgent",
            description="Fetches live odds, line movement, and injury data for sports markets"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        now = datetime.now(timezone.utc).isoformat()

        if not _ODDS_AVAILABLE:
            return self._mock_evidence(market, now)

        try:
            odds = self._fetch_odds(market)
            injuries = self._fetch_injuries(market)
        except Exception as e:
            print(f"[{self.name}] Data fetch error: {e}")
            return []

        return [
            self._odds_chunk(market, odds, now),
            self._injury_chunk(market, injuries, now),
        ]

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_odds(self, market: Market) -> dict:
        # TODO: replace with real TheOddsAPI call
        # import httpx
        # sport = self._detect_sport(market.category)
        # r = httpx.get(
        #     f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
        #     params={
        #         "apiKey": os.getenv("ODDS_API_KEY"),
        #         "regions": "us",
        #         "markets": "h2h,spreads",
        #         "bookmakers": "draftkings,fanduel",
        #     },
        #     timeout=10,
        # )
        # r.raise_for_status()
        # return r.json()
        raise NotImplementedError("Set ODDS_API_KEY and implement _fetch_odds")

    def _fetch_injuries(self, market: Market) -> list:
        # TODO: replace with real ESPN injury report call
        # import httpx
        # sport = self._detect_sport(market.category)
        # league = self._detect_league(market)
        # r = httpx.get(
        #     f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/injuries",
        #     timeout=10,
        # )
        # r.raise_for_status()
        # return r.json().get("injuries", [])
        raise NotImplementedError("Implement _fetch_injuries using ESPN API")

    # ------------------------------------------------------------------
    # EvidenceChunk builders
    # ------------------------------------------------------------------

    def _odds_chunk(self, market: Market, odds: dict, now: str) -> EvidenceChunk:
        # TODO: format real odds API response into readable text
        text = (
            f"=== Odds Data: {market.title} ===\n"
            f"Market: {market.question}\n"
            f"Raw odds data: {odds}\n"
        )
        return EvidenceChunk(
            source_type="sports_video",
            text=text,
            source_url="https://the-odds-api.com",
            timestamp=now,
            confidence=1.0,
            metadata={"agent": self.name},
        )

    def _injury_chunk(self, market: Market, injuries: list, now: str) -> EvidenceChunk:
        # TODO: format real ESPN injury response into readable text
        text = (
            f"=== Injury Report: {market.title} ===\n"
            f"Raw injury data: {injuries}\n"
        )
        return EvidenceChunk(
            source_type="sports_video",
            text=text,
            source_url="https://site.api.espn.com",
            timestamp=now,
            confidence=1.0,
            metadata={"agent": self.name},
        )

    # ------------------------------------------------------------------
    # Mock fallback
    # ------------------------------------------------------------------

    def _mock_evidence(self, market: Market, now: str) -> List[EvidenceChunk]:
        print(f"[{self.name}] ODDS_API_KEY not set — returning mock evidence")
        return [
            EvidenceChunk(
                source_type="sports_video",
                text=(
                    f"=== Odds Data (MOCK): {market.title} ===\n"
                    f"Market: {market.question}\n"
                    f"Current line: Team A -110 / Team B +100\n"
                    f"Line movement: moved from -105 to -110 in the last 2 hours\n"
                ),
                source_url=None,
                timestamp=now,
                confidence=0.0,
                metadata={"mock": True},
            ),
            EvidenceChunk(
                source_type="sports_video",
                text=(
                    f"=== Injury Report (MOCK): {market.title} ===\n"
                    f"No significant injuries reported for either team.\n"
                ),
                source_url=None,
                timestamp=now,
                confidence=0.0,
                metadata={"mock": True},
            ),
        ]
