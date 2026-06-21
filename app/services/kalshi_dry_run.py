"""
Dry-run Kalshi trade logger.

Formats and stores what a live Kalshi trade WOULD look like.
ENABLE_LIVE_TRADING must be false (enforced at runtime).

Writes:
  market:{market_id}:kalshi_dry_run   → latest trade for that market
  stream:kalshi:dry_run_trades        → Redis Stream of all triggered trades
"""

import json
import os
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_redis():
    import redis
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(url, decode_responses=True)


def log_dry_run_trade(
    market_id: str,
    market_question: str,
    decision,
    trigger_headline: str,
) -> dict:
    """
    Log a dry-run Kalshi trade to Redis.

    Args:
        market_id: Unique market identifier (slugified event hash)
        market_question: Auto-generated YES/NO question
        decision: Decision object with recommendation/confidence/fair_probability/reasoning
        trigger_headline: The news headline that triggered this analysis

    Returns:
        The trade dict that was logged
    """
    if os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true":
        raise RuntimeError("ENABLE_LIVE_TRADING is true — refusing to run in dry-run mode")

    rec = decision.recommendation
    if rec == "YES":
        action, contract = "BUY YES", "YES"
    elif rec == "NO":
        action, contract = "BUY NO", "NO"
    else:
        action, contract = "NO_TRADE", "HOLD"

    trade = {
        "timestamp": _utc_now(),
        "market_id": market_id,
        "market_question": market_question,
        "trigger_headline": trigger_headline,
        "action": action,
        "contract": contract,
        "confidence": decision.confidence,
        "fair_probability": decision.fair_probability,
        "reasoning": decision.reasoning,
        "mode": "dry_run",
        "kalshi_env": os.getenv("KALSHI_ENV", "demo"),
    }

    try:
        r = _get_redis()
        r.set(f"market:{market_id}:kalshi_dry_run", json.dumps(trade))
        r.xadd(
            "stream:kalshi:dry_run_trades",
            {
                "market_id": market_id,
                "action": action,
                "confidence": str(decision.confidence),
                "fair_probability": str(decision.fair_probability or ""),
                "question": market_question[:200],
                "headline": trigger_headline[:200],
                "timestamp": trade["timestamp"],
            },
        )
        print(f"[KalshiDryRun] {action} logged → market:{market_id}:kalshi_dry_run")
    except Exception as e:
        print(f"[KalshiDryRun] Redis write failed: {e}")

    return trade


def get_recent_trades(count: int = 20) -> list[dict]:
    """Read the last N dry-run trades from the Redis Stream."""
    try:
        r = _get_redis()
        entries = r.xrevrange("stream:kalshi:dry_run_trades", count=count)
        return [fields for _, fields in entries]
    except Exception:
        return []
