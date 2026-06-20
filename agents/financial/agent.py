"""
Financial research agent.

Responsibility: fetch raw Kalshi market data (price, volume, orderbook) and
emit a ResearchOutput. No LLM reasoning here — that lives in the decision agent.

Requires env vars (see kalshi_client.py):
    KALSHI_KEY_ID, KALSHI_PRIVATE_KEY_PATH (or KALSHI_PRIVATE_KEY)

Falls back to mock data if Kalshi env vars are not set.

Run standalone:
    python agents/financial/agent.py KXBTCD-25DEC31-B100000
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from schemas.schema import ResearchOutput, FinancialEvidence

_KALSHI_AVAILABLE = bool(os.getenv("KALSHI_KEY_ID"))


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_market(market_id: str) -> dict:
    if not _KALSHI_AVAILABLE:
        return {
            "ticker": market_id,
            "title": f"Mock market title for {market_id}",
            "last_price": 55,
            "previous_price": 52,
            "volume": 1200,
            "status": "open",
            "close_time": "2025-12-31T23:59:59Z",
        }

    from agents.financial.kalshi_client import get_market
    return get_market(market_id)


def fetch_orderbook(market_id: str) -> dict:
    if not _KALSHI_AVAILABLE:
        return {
            "yes": [[54, 50], [53, 120], [52, 300]],
            "no":  [[46, 80], [45, 200], [44, 150]],
        }

    from agents.financial.kalshi_client import get_orderbook
    return get_orderbook(market_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def summarize_orderbook(ob: dict) -> str:
    def fmt(side: list) -> str:
        return ", ".join(f"{p}¢×{q}" for p, q in (side or [])[:3])
    return f"YES: [{fmt(ob.get('yes', []))}] | NO: [{fmt(ob.get('no', []))}]"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_financial_agent(market_id: str) -> ResearchOutput:
    try:
        market = fetch_market(market_id)
        ob = fetch_orderbook(market_id)
        data_quality = 1.0 if _KALSHI_AVAILABLE else 0.0
    except Exception as e:
        return ResearchOutput(
            agent="financial",
            market_id=market_id,
            applicable=False,
            evidence=FinancialEvidence(
                market_id=market_id,
                last_price=0.0,
                raw_text=f"Data fetch failed: {e}",
            ),
            data_quality=0.0,
            sources=[],
        )

    last_price = market["last_price"] / 100
    prev_price = market.get("previous_price", market["last_price"]) / 100
    price_change_pct = ((last_price - prev_price) / prev_price * 100) if prev_price else 0.0

    evidence = FinancialEvidence(
        market_id=market_id,
        last_price=last_price,
        price_change_pct=round(price_change_pct, 2),
        volume=market.get("volume", 0),
        orderbook_summary=summarize_orderbook(ob),
        raw_text=(
            f"title={market.get('title')} "
            f"status={market.get('status')} "
            f"close={market.get('close_time')}"
        ),
    )

    return ResearchOutput(
        agent="financial",
        market_id=market_id,
        applicable=True,
        evidence=evidence,
        data_quality=data_quality,
        sources=[f"kalshi.com/markets/{market_id}"],
    )


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "KXBTCD-25DEC31-B100000"
    print(run_financial_agent(market_id).model_dump_json(indent=2))
