"""
Thin Kalshi API client with RSA-based request signing.

Required env vars:
    KALSHI_KEY_ID          — your API key ID from Kalshi dashboard
    KALSHI_PRIVATE_KEY_PATH — path to your RSA private key .pem file
                              (OR set KALSHI_PRIVATE_KEY with the PEM content inline,
                               replacing literal newlines with \\n)

Optional:
    KALSHI_API_BASE        — defaults to production; swap for demo:
                             https://demo-api.kalshi.co/trade-api/v2
"""

import base64
import os
import time

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE_URL = os.getenv("KALSHI_API_BASE", "https://trading-api.kalshi.com/trade-api/v2")


def _load_private_key():
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if key_path:
        with open(key_path, "rb") as f:
            pem = f.read()
    else:
        # Inline PEM — allow \n to be stored as literal backslash-n in env
        pem = os.getenv("KALSHI_PRIVATE_KEY", "").replace("\\n", "\n").encode()

    if not pem:
        raise ValueError(
            "Set KALSHI_PRIVATE_KEY_PATH (path to .pem) or KALSHI_PRIVATE_KEY (inline PEM)"
        )
    return serialization.load_pem_private_key(pem, password=None, backend=default_backend())


def _auth_headers(method: str, path: str) -> dict:
    """
    Kalshi RSA auth: sign (timestamp_ms + METHOD + /path) with your private key.
    path must be the full API path, e.g. /trade-api/v2/markets/{ticker}
    Do NOT include query params or the base hostname.
    """
    key_id = os.getenv("KALSHI_KEY_ID")
    if not key_id:
        raise ValueError("Set KALSHI_KEY_ID env var")

    private_key = _load_private_key()
    timestamp_ms = str(int(time.time() * 1000))
    message = (timestamp_ms + method.upper() + path).encode("utf-8")
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())

    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "Content-Type": "application/json",
    }


def get_market(market_id: str) -> dict:
    """Returns the market object for a given ticker."""
    path = f"/trade-api/v2/markets/{market_id}"
    r = httpx.get(f"{BASE_URL}/markets/{market_id}", headers=_auth_headers("GET", path), timeout=10)
    r.raise_for_status()
    return r.json()["market"]


def get_orderbook(market_id: str, depth: int = 5) -> dict:
    """Returns orderbook dict with 'yes' and 'no' lists of [price_cents, quantity]."""
    path = f"/trade-api/v2/markets/{market_id}/orderbook"
    r = httpx.get(
        f"{BASE_URL}/markets/{market_id}/orderbook",
        headers=_auth_headers("GET", path),
        params={"depth": depth},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("orderbook", {})
