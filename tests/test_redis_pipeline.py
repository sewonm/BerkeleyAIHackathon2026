"""
Tests the pipeline: Kalshi API -> Redis

Runs: fetch market data -> write snapshot + claims -> read back from Redis

Usage:
    python tests/test_redis_pipeline.py [MARKET_ID]

Requires: Redis running locally (redis-server) + .env with Kalshi credentials
"""

import asyncio
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
import base64
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import httpx

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services.redis_service import (
    ping,
    set_market_snapshot,
    get_market_snapshot,
    append_claims,
    get_claims,
    clear_claims,
)

PROD_BASE = "https://trading-api.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"
BASE_URL = PROD_BASE if os.getenv("KALSHI_ENV") == "production" else DEMO_BASE


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
    if not key_id:
        raise SystemExit("Set KALSHI_API_KEY_ID in .env")
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


async def run(market_id: str):
    now = datetime.now(timezone.utc).isoformat()

    print("\n-- Step 0: Redis health check --")
    if not ping():
        raise SystemExit("Redis is not running. Start it with: redis-server")
    print("OK Redis connected")

    print(f"\n-- Step 1: Fetch Kalshi market data ({market_id}) --")
    market = await fetch_market(market_id)
    ob = await fetch_orderbook(market_id)
    print(f"OK Market: {market.get('title', market_id)}")
    print(f"  YES ask: ${market.get('yes_ask_dollars')}  YES bid: ${market.get('yes_bid_dollars')}")
    print(f"  Volume: {market.get('volume_fp')}  Status: {market.get('status')}")

    print("\n-- Step 2: Write snapshot -> Redis --")
    yes_ask = float(market.get("yes_ask_dollars") or 0)
    yes_bid = float(market.get("yes_bid_dollars") or 0)
    snapshot = {
        "market_id": market_id,
        "question": market.get("title", ""),
        "yes_price": round((yes_ask + yes_bid) / 2, 4) if (yes_ask + yes_bid) > 0 else 0,
        "yes_ask": yes_ask,
        "yes_bid": yes_bid,
        "no_ask": float(market.get("no_ask_dollars") or 0),
        "no_bid": float(market.get("no_bid_dollars") or 0),
        "volume": float(market.get("volume_fp") or 0),
        "open_interest": float(market.get("open_interest_fp") or 0),
        "status": market.get("status"),
        "close_time": market.get("close_time"),
        "timestamp": now,
    }
    set_market_snapshot(market_id, snapshot)
    print("OK Snapshot written")

    print("\n-- Step 3: Write evidence claims -> Redis --")
    clear_claims(market_id)

    yes_levels = ob.get("yes", [])
    no_levels = ob.get("no", [])
    yes_depth = sum(q for _, q in yes_levels)
    no_depth = sum(q for _, q in no_levels)
    imbalance = "YES-heavy" if yes_depth > no_depth else "NO-heavy" if no_depth > yes_depth else "balanced"

    claims = [
        {
            "claim_id": f"{market_id}_snapshot",
            "claim": (
                f"YES mid: ${snapshot['yes_price']:.2f} | "
                f"Volume: {snapshot['volume']:,.0f} | Status: {snapshot['status']}"
            ),
            "source_type": "financial_research",
            "source_name": "kalshi_api",
            "confidence": 1.0,
            "market_relevance": 0.95,
            "raw_tokens": 80,
            "timestamp": now,
        },
        {
            "claim_id": f"{market_id}_orderbook",
            "claim": (
                f"Orderbook imbalance: {imbalance} "
                f"(YES depth {yes_depth} vs NO depth {no_depth})"
            ),
            "source_type": "financial_research",
            "source_name": "kalshi_orderbook",
            "confidence": 1.0,
            "market_relevance": 0.9,
            "raw_tokens": 60,
            "timestamp": now,
        },
    ]
    append_claims(market_id, claims)
    print(f"OK {len(claims)} claims written")

    print("\n-- Step 4: Read back from Redis --")
    stored_snapshot = get_market_snapshot(market_id)
    stored_claims = get_claims(market_id)

    print(f"OK Snapshot: yes_price={stored_snapshot['yes_price']}  volume={stored_snapshot['volume']}")
    print(f"OK Claims ({len(stored_claims)} total):")
    for c in stored_claims:
        print(f"   [{c['source_type']}] {c['claim']}")

    print("\nPASSED Pipeline test passed — Kalshi -> Redis working end to end\n")


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "KXTEMPNYCH-26JUN2021-T86.99"
    asyncio.run(run(market_id))
