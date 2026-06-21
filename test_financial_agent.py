"""
Direct test of Kalshi API calls used by financial_research_agent.
No uAgents/blockchain needed — just verifies the API auth and data fetch work.

Usage:
    python test_financial_agent.py [MARKET_ID]

Example:
    python test_financial_agent.py INXD-23DEC31-B3000
"""

import asyncio
import sys
import os
import base64
import time
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import httpx

load_dotenv()

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
        raise SystemExit("KALSHI_API_KEY_ID not set in .env")
    key = load_key()
    ts = str(int(time.time() * 1000))
    sig = key.sign((ts + method.upper() + path).encode(), padding.PKCS1v15(), hashes.SHA256())
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Content-Type": "application/json",
    }


async def test(market_id: str):
    print(f"\nTesting against: {BASE_URL}")
    print(f"Market ID: {market_id}\n")

    async with httpx.AsyncClient(timeout=10) as client:
        # Test 1: fetch market
        path = f"/trade-api/v2/markets/{market_id}"
        print(f"GET {path}")
        r = await client.get(f"{BASE_URL}/markets/{market_id}", headers=auth_headers("GET", path))
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            m = r.json()["market"]
            print(f"  Title:      {m.get('title')}")
            print(f"  YES ask:    ${m.get('yes_ask_dollars')}")
            print(f"  YES bid:    ${m.get('yes_bid_dollars')}")
            print(f"  Volume:     {m.get('volume_fp')}")
            print(f"  Status:     {m.get('status')}")
        else:
            print(f"  Error: {r.text}")

        print()

        # Test 2: fetch orderbook
        path2 = f"/trade-api/v2/markets/{market_id}/orderbook"
        print(f"GET {path2}")
        r2 = await client.get(f"{BASE_URL}/markets/{market_id}/orderbook",
                              headers=auth_headers("GET", path2), params={"depth": 5})
        print(f"Status: {r2.status_code}")
        if r2.status_code == 200:
            ob = r2.json().get("orderbook", {})
            print(f"  YES levels: {ob.get('yes', [])[:3]}")
            print(f"  NO levels:  {ob.get('no', [])[:3]}")
        else:
            print(f"  Error: {r2.text}")


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "INXD-23DEC31-B3000"
    asyncio.run(test(market_id))