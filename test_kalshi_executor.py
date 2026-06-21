"""
Quick smoke test for the Kalshi executor.

Steps:
  1. Dry-run validation (no network call)
  2. Auth check — GET /portfolio/balance to confirm key + PEM work
  3. Live order submit (only if you pass --live)

Usage:
  python test_kalshi_executor.py           # dry-run + auth check only
  python test_kalshi_executor.py --live    # also submits a real $1 order to demo
"""

from __future__ import annotations
import sys
import os
import json
import base64
import datetime
from pathlib import Path
from urllib.parse import urlparse

# --- repo root on path so app.* imports work ---
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

# Always use the exec key for this test
exec_pem = REPO_ROOT / "kalshi_exec_private_key.pem"
if exec_pem.exists():
    os.environ["KALSHI_PRIVATE_KEY_PATH"] = str(exec_pem)

from app.schemas.execution import TradeDecision, ExecutionResult
from app.services.kalshi_executor import (
    build_order_from_decision,
    fetch_live_ticker,
    load_private_key,
    create_signature,
    execute_decision,
    KALSHI_API_KEY,
    KALSHI_PRIVATE_KEY_PATH,
    KALSHI_BASE_URL,
)
import requests

LIVE = "--live" in sys.argv

# ── 1. Env check ──────────────────────────────────────────────────────────────
print("\n=== ENV CHECK ===")
print(f"KALSHI_EXEC_API_KEY_ID set: {bool(KALSHI_API_KEY)} (len={len(KALSHI_API_KEY or '')})")
print(f"KALSHI_PRIVATE_KEY_PATH:    {KALSHI_PRIVATE_KEY_PATH}")
print(f"KALSHI_BASE_URL:            {KALSHI_BASE_URL}")

# ── 2. Dry-run validation ──────────────────────────────────────────────────────
print("\n=== DRY-RUN VALIDATION ===")

# Fetch a real ticker from the demo account so validation uses a market that exists.
_ticker = "PLACEHOLDER-TICKER"
_yes_price = 0.50
_market_question = "Live market from demo account"
if KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH:
    try:
        _ticker, _yes_price = fetch_live_ticker()
        _market_question = f"Live demo market: {_ticker}"
        print(f"Fetched live ticker: {_ticker}  yes_price={_yes_price:.2f}")
    except Exception as _e:
        print(f"Could not fetch live ticker ({_e}), using placeholder for dry-run")
else:
    print("No credentials set — using placeholder ticker for dry-run")

decision = TradeDecision(
    ticker=_ticker,
    market_question=_market_question,
    recommendation="YES",
    confidence=0.80,
    fair_probability=0.60,
    edge=0.10,
    current_yes_price=_yes_price,
    max_order_dollars=1.00,
    dry_run=True,
)
result = build_order_from_decision(decision)
print(f"approved:            {result.approved}")
print(f"action_taken:        {result.action_taken}")
print(f"estimated_contracts: {result.estimated_contracts}")
print(f"estimated_cost:      ${result.estimated_cost_dollars}")
print(f"reason:              {result.reason}")
print(f"order_payload:\n{json.dumps(result.order_payload, indent=2)}")
assert result.approved, "Dry-run should be approved"
print("PASS: Dry-run passed")

# ── 3. Auth check — GET /portfolio/balance ─────────────────────────────────────
print("\n=== AUTH CHECK (GET /portfolio/balance) ===")
try:
    private_key = load_private_key()
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    path = "/trade-api/v2/portfolio/balance"
    sig = create_signature(private_key, timestamp, "GET", path)

    headers = {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }
    resp = requests.get(KALSHI_BASE_URL + "/portfolio/balance", headers=headers, timeout=10)
    print(f"HTTP {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
    if resp.status_code == 200:
        print("PASS: Auth check passed -- API key + PEM are working")
    else:
        print("FAIL: Auth check failed")
except Exception as e:
    print(f"✗ Auth check error: {e}")

# ── 4. Live order (only with --live flag) ──────────────────────────────────────
if LIVE:
    print("\n=== LIVE ORDER SUBMIT ===")
    try:
        live_ticker, live_yes_price = fetch_live_ticker()
        print(f"Fetched live ticker for order: {live_ticker}  yes_price={live_yes_price:.2f}")
    except Exception as _e:
        print(f"FAIL: Could not fetch live ticker: {_e}")
        sys.exit(1)

    live_decision = TradeDecision(
        ticker=live_ticker,
        market_question=f"Live demo market: {live_ticker}",
        recommendation="YES",
        confidence=0.80,
        fair_probability=0.60,
        edge=0.10,
        current_yes_price=live_yes_price,
        max_order_dollars=1.00,
        dry_run=False,
    )
    os.environ["ALLOW_LIVE_TRADING"] = "true"
    live_result = execute_decision(live_decision)
    print(f"approved:         {live_result.approved}")
    print(f"action_taken:     {live_result.action_taken}")
    print(f"reason:           {live_result.reason}")
    print(f"kalshi_response:\n{json.dumps(live_result.kalshi_response, indent=2)}")
else:
    print("\n(skipping live order — run with --live to submit a real demo order)")
