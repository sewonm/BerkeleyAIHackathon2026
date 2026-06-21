"""
Test: financial research agent → Redis

Fetches live Kalshi market data, writes snapshot + claims to Redis,
then reads them back to confirm the pipeline works.

Usage:
    python test_redis_pipeline.py [MARKET_ID]

Example:
    python test_redis_pipeline.py KXTEMPNYCH-26JUN2021-T86.99
"""

import asyncio
import sys
import os
import base64
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import httpx

load_dotenv()

# ---------------------------------------------------------------------------
# Kalshi auth (same as financial_research_agent)
# ---------------------------------------------------------------------------

DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"
BASE_URL = DEMO_BASE


def load_key():
    inline = os.getenv("KALSHI_PRIVATE_KEY", "").replace("\\n", "\n").strip()
    if inline:
        return serialization.load_pem_private_key(inline.encode(), password=None, backend=default_backend())
    path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
    if path:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    raise SystemExit("Set KALSHI_PRIVATE_KEY or KALSHI_PRIVATE_KEY_PATH in .env")


def auth_headers(method: str, path: str) -> dict:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    key = load_key()
    ts = str(int(time.time() * 1000))
    sig = key.sign((ts + method.upper() + path).encode(), padding.PKCS1v15(), hashes.SHA256())
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }


async def fetch_market(market_id: str) -> dict:
    path = f"/trade-api/v2/markets/{market_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/markets/{market_id}", headers=auth_headers("GET", path))
    r.raise_for_status()
    return r.json()["market"]


async def fetch_orderbook(market_id: str) -> dict:
    path = f"/trade-api/v2/markets/{market_id}/orderbook"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{BASE_URL}/markets/{market_id}/orderbook",
            headers=auth_headers("GET", path),
            params={"depth": 5},
        )
    r.raise_for_status()
    return r.json().get("orderbook", {})


# ---------------------------------------------------------------------------
# Redis pipeline
# ---------------------------------------------------------------------------

async def run(market_id: str):
    from app.services.redis_service import ping, set_market_snapshot, get_market_snapshot, append_claims, get_claims, clear_claims

    # 1. Check Redis connection
    print("\n[1] Checking Redis connection...")
    if not ping():
        raise SystemExit("Redis not reachable — is redis-server running?")
    print("    ✓ Redis connected")

    # 2. Fetch from Kalshi
    print(f"\n[2] Fetching Kalshi data for {market_id}...")
    market = await fetch_market(market_id)
    ob = await fetch_orderbook(market_id)

    yes_ask = float(market.get("yes_ask_dollars") or 0)
    yes_bid = float(market.get("yes_bid_dollars") or 0)
    yes_mid = (yes_ask + yes_bid) / 2

    yes_levels = ob.get("yes", [])
    no_levels = ob.get("no", [])
    yes_depth = sum(q for _, q in yes_levels)
    no_depth = sum(q for _, q in no_levels)
    imbalance = "YES-heavy" if yes_depth > no_depth else "NO-heavy" if no_depth > yes_depth else "balanced"

    print(f"    Title:    {market.get('title')}")
    print(f"    YES mid:  ${yes_mid:.2f}")
    print(f"    Volume:   {market.get('volume_fp')}")
    print(f"    Orderbook imbalance: {imbalance}")

    # 3. Write snapshot to Redis
    print(f"\n[3] Writing snapshot to Redis...")
    snapshot = {
        "market_id": market_id,
        "question": market.get("subtitle") or market.get("title"),
        "yes_price": round(yes_mid, 4),
        "yes_ask": yes_ask,
        "yes_bid": yes_bid,
        "no_ask": float(market.get("no_ask_dollars") or 0),
        "no_bid": float(market.get("no_bid_dollars") or 0),
        "volume": float(market.get("volume_fp") or 0),
        "open_interest": float(market.get("open_interest_fp") or 0),
        "status": market.get("status"),
        "orderbook_imbalance": imbalance,
        "yes_depth": yes_depth,
        "no_depth": no_depth,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    set_market_snapshot(market_id, snapshot)
    print(f"    ✓ Written to Redis key: market:{market_id}:snapshot")

    # 4. Write evidence claims
    print(f"\n[4] Writing evidence claims to Redis...")
    clear_claims(market_id)
    claims = [
        {
            "claim_id": "financial_001",
            "claim": f"YES mid price is ${yes_mid:.2f} (ask ${yes_ask:.2f}, bid ${yes_bid:.2f})",
            "source_type": "financial_research",
            "supports": "market_data",
            "confidence": 1.0,
            "market_relevance": 0.95,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "claim_id": "financial_002",
            "claim": f"Orderbook is {imbalance} (YES depth: {yes_depth}, NO depth: {no_depth})",
            "source_type": "financial_research",
            "supports": "orderbook",
            "confidence": 1.0,
            "market_relevance": 0.9,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]
    append_claims(market_id, claims)
    print(f"    ✓ Written {len(claims)} claims to Redis key: market:{market_id}:claims")

    # 5. Read back and verify
    print(f"\n[5] Reading back from Redis to verify...")
    stored_snapshot = get_market_snapshot(market_id)
    stored_claims = get_claims(market_id)

    print(f"    Snapshot yes_price: ${stored_snapshot['yes_price']}")
    print(f"    Snapshot imbalance: {stored_snapshot['orderbook_imbalance']}")
    print(f"    Claims count: {len(stored_claims)}")
    for c in stored_claims:
        print(f"      · [{c['source_type']}] {c['claim']}")

    print(f"\n✅ Pipeline test complete — financial agent → Redis working.\n")


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "KXTEMPNYCH-26JUN2021-T86.99"
    asyncio.run(run(market_id))