"""Kalshi API service — RSA-signed requests for market data and orderbook."""

import base64
import os
import time

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

PROD_BASE = "https://trading-api.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"


class KalshiService:
    """
    Kalshi API client with RSA request signing.

    Required env vars:
        KALSHI_KEY_ID            — your API key ID from the Kalshi dashboard
        KALSHI_PRIVATE_KEY_PATH  — path to your RSA private key .pem file
                                   OR set KALSHI_PRIVATE_KEY with inline PEM
                                   (replace literal newlines with \\n)

    Optional:
        KALSHI_ENV  — "demo" (default) or "production"
    """

    def __init__(self, api_key: str = None, environment: str = None):
        env = environment or os.getenv("KALSHI_ENV", "demo")
        self.base_url = PROD_BASE if env == "production" else DEMO_BASE
        self.key_id = os.getenv("KALSHI_KEY_ID", api_key)
        self._private_key = None  # lazy-loaded on first request

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _load_key(self):
        if self._private_key is not None:
            return self._private_key

        key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
        if key_path:
            with open(key_path, "rb") as f:
                pem = f.read()
        else:
            pem = os.getenv("KALSHI_PRIVATE_KEY", "").replace("\\n", "\n").encode()

        if not pem:
            raise ValueError(
                "Set KALSHI_PRIVATE_KEY_PATH (path to .pem) or KALSHI_PRIVATE_KEY (inline PEM)"
            )
        self._private_key = serialization.load_pem_private_key(
            pem, password=None, backend=default_backend()
        )
        return self._private_key

    def _auth_headers(self, method: str, path: str) -> dict:
        """
        Sign: timestamp_ms + METHOD + /path  (no query string, no hostname).
        path should be the full API path, e.g. /trade-api/v2/markets/{ticker}
        """
        if not self.key_id:
            raise ValueError("Set KALSHI_KEY_ID env var")

        key = self._load_key()
        timestamp_ms = str(int(time.time() * 1000))
        message = (timestamp_ms + method.upper() + path).encode("utf-8")
        signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())

        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def get_market(self, market_id: str) -> dict:
        """Returns the raw market object for a given ticker."""
        path = f"/trade-api/v2/markets/{market_id}"
        r = httpx.get(
            f"{self.base_url}/markets/{market_id}",
            headers=self._auth_headers("GET", path),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["market"]

    def get_market_price(self, market_id: str) -> float:
        """Returns the current YES price as a float (0.0–1.0)."""
        market = self.get_market(market_id)
        return market.get("last_price", 0) / 100

    def get_orderbook(self, market_id: str, depth: int = 5) -> dict:
        """Returns orderbook with 'yes' and 'no' lists of [price_cents, quantity]."""
        path = f"/trade-api/v2/markets/{market_id}/orderbook"
        r = httpx.get(
            f"{self.base_url}/markets/{market_id}/orderbook",
            headers=self._auth_headers("GET", path),
            params={"depth": depth},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("orderbook", {})

    def place_order(self, market_id: str, side: str, quantity: int, price: float):
        """TODO: Place a limit order."""
        raise NotImplementedError("Order placement not yet implemented")

    def cancel_order(self, order_id: str):
        """TODO: Cancel an order."""
        raise NotImplementedError("Order cancellation not yet implemented")

    def get_balance(self):
        """TODO: Get account balance."""
        raise NotImplementedError("Balance fetch not yet implemented")
