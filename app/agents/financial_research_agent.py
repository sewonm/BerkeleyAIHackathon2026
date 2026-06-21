"""Financial research agent — fetches raw Kalshi market data for the compression agent."""

import os
from datetime import datetime, timezone
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.services.kalshi_service import KalshiService


class FinancialResearchAgent(BaseAgent):
    """
    Fetches live Kalshi market data (price, volume, orderbook) and returns it
    as EvidenceChunks for the compression agent.

    No LLM reasoning here — raw data only.

    Requires env vars:
        KALSHI_KEY_ID + KALSHI_PRIVATE_KEY_PATH (or KALSHI_PRIVATE_KEY)
    Falls back to mock data if those are not set.
    """

    def __init__(self):
        super().__init__(
            name="FinancialResearchAgent",
            description="Fetches live Kalshi market microstructure data (price, volume, orderbook)"
        )
        self.kalshi = KalshiService() if os.getenv("KALSHI_API_KEY_ID") else None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, market: Market) -> List[EvidenceChunk]:
        now = datetime.now(timezone.utc).isoformat()

        if not self.kalshi:
            return self._mock_evidence(market, now)

        try:
            raw_market = self.kalshi.get_market(market.market_id)
            raw_ob = self.kalshi.get_orderbook(market.market_id, depth=5)
        except Exception as e:
            print(f"[{self.name}] Kalshi API error: {e}")
            return []

        return [
            self._market_chunk(market, raw_market, now),
            self._orderbook_chunk(market, raw_market, raw_ob, now),
        ]

    # ------------------------------------------------------------------
    # EvidenceChunk builders
    # ------------------------------------------------------------------

    def _market_chunk(self, market: Market, raw: dict, now: str) -> EvidenceChunk:
        # Kalshi API returns prices as dollar strings (0.0–1.0), not integer cents
        yes_ask = float(raw.get("yes_ask_dollars") or 0)
        yes_bid = float(raw.get("yes_bid_dollars") or 0)
        yes_mid = (yes_ask + yes_bid) / 2 if (yes_ask + yes_bid) > 0 else 0.0

        prev_ask = float(raw.get("previous_yes_ask_dollars") or 0)
        prev_bid = float(raw.get("previous_yes_bid_dollars") or 0)
        prev_mid = (prev_ask + prev_bid) / 2

        if prev_mid > 0:
            price_change = ((yes_mid - prev_mid) / prev_mid) * 100
            price_change_str = f"{price_change:+.2f}%"
        else:
            price_change = None
            price_change_str = "N/A (new market)"

        volume = float(raw.get("volume_fp") or 0)
        open_interest = float(raw.get("open_interest_fp") or 0)

        text = (
            f"=== Kalshi Market Data: {raw.get('title', market.market_id)} ===\n"
            f"Market ID: {market.market_id}\n"
            f"Question: {market.question}\n"
            f"YES Ask: ${yes_ask:.2f} | YES Bid: ${yes_bid:.2f} | Mid: ${yes_mid:.2f}\n"
            f"NO Ask:  ${float(raw.get('no_ask_dollars') or 0):.2f} | "
            f"NO Bid: ${float(raw.get('no_bid_dollars') or 0):.2f}\n"
            f"Price Change (recent): {price_change_str}\n"
            f"Volume: {volume:,.2f} contracts | Open Interest: {open_interest:,.2f}\n"
            f"Status: {raw.get('status', 'unknown')} | "
            f"Closes: {raw.get('close_time', 'unknown')}\n"
        )

        return EvidenceChunk(
            source_type="financial_research",
            text=text,
            source_url=f"https://kalshi.com/markets/{market.market_id}",
            timestamp=now,
            confidence=1.0,
            metadata={
                "yes_mid": round(yes_mid, 4),
                "yes_ask": yes_ask,
                "yes_bid": yes_bid,
                "price_change_pct": round(price_change, 2) if price_change is not None else None,
                "volume": volume,
                "open_interest": open_interest,
                "status": raw.get("status"),
            },
        )

    def _orderbook_chunk(self, market: Market, raw_market: dict, ob: dict, now: str) -> EvidenceChunk:
        def fmt_side(side: list) -> str:
            return ", ".join(f"{p}¢×{q}" for p, q in (side or [])[:5])

        yes_levels = ob.get("yes", [])
        no_levels = ob.get("no", [])

        yes_total = sum(q for _, q in yes_levels)
        no_total = sum(q for _, q in no_levels)
        imbalance = "YES-heavy" if yes_total > no_total else "NO-heavy" if no_total > yes_total else "balanced"

        text = (
            f"=== Kalshi Orderbook: {raw_market.get('title', market.market_id)} ===\n"
            f"YES bids (price×qty): {fmt_side(yes_levels)}\n"
            f"NO bids  (price×qty): {fmt_side(no_levels)}\n"
            f"Top-5 YES depth: {yes_total:,} contracts | "
            f"Top-5 NO depth: {no_total:,} contracts\n"
            f"Orderbook imbalance: {imbalance}\n"
        )

        return EvidenceChunk(
            source_type="financial_research",
            text=text,
            source_url=f"https://kalshi.com/markets/{market.market_id}",
            timestamp=now,
            confidence=1.0,
            metadata={
                "yes_depth": yes_total,
                "no_depth": no_total,
                "imbalance": imbalance,
            },
        )

    # ------------------------------------------------------------------
    # Mock fallback (no API keys needed)
    # ------------------------------------------------------------------

    def _mock_evidence(self, market: Market, now: str) -> List[EvidenceChunk]:
        print(f"[{self.name}] KALSHI_KEY_ID not set — returning mock evidence")
        return [
            EvidenceChunk(
                source_type="financial_research",
                text=(
                    f"=== Kalshi Market Data (MOCK): {market.title} ===\n"
                    f"Market ID: {market.market_id}\n"
                    f"Current YES Price: 0.55 (55¢)\n"
                    f"Price Change (recent): +2.30%\n"
                    f"Volume: 1,200 contracts\n"
                    f"Status: open | Closes: 2025-12-31T23:59:59Z\n"
                ),
                source_url=None,
                timestamp=now,
                confidence=0.0,
                metadata={"mock": True},
            ),
            EvidenceChunk(
                source_type="financial_research",
                text=(
                    f"=== Kalshi Orderbook (MOCK): {market.title} ===\n"
                    f"YES bids: 54¢×50, 53¢×120, 52¢×300, 51¢×500, 50¢×800\n"
                    f"NO bids:  46¢×80, 45¢×200, 44¢×150, 43¢×300, 42¢×500\n"
                    f"Top-5 YES depth: 1,770 contracts | Top-5 NO depth: 1,230 contracts\n"
                    f"Orderbook imbalance: YES-heavy\n"
                ),
                source_url=None,
                timestamp=now,
                confidence=0.0,
                metadata={"mock": True},
            ),
        ]
