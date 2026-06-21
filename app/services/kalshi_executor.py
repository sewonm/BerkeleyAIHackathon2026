import os
import math
import uuid
import json
import base64
import datetime
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.schemas.execution import TradeDecision, ExecutionResult


MIN_CONFIDENCE = float(os.getenv("EXECUTOR_MIN_CONFIDENCE", "0.70"))
MIN_EDGE = float(os.getenv("EXECUTOR_MIN_EDGE", "0.05"))
MAX_ORDER_DOLLARS = float(os.getenv("EXECUTOR_MAX_ORDER_DOLLARS", "5.00"))
MAX_CONTRACTS = int(os.getenv("EXECUTOR_MAX_CONTRACTS", "10"))

KALSHI_BASE_URL = os.getenv(
    "KALSHI_BASE_URL",
    "https://external-api.demo.kalshi.co/trade-api/v2",
)

KALSHI_API_KEY = os.getenv("KALSHI_API_KEY")
KALSHI_PRIVATE_KEY_PATH = os.getenv("KALSHI_PRIVATE_KEY_PATH")


def build_order_from_decision(decision: TradeDecision) -> ExecutionResult:
    """
    Pure validation + order construction.

    This function does NOT submit to Kalshi.
    It only decides whether the trade passes risk checks and builds the payload.
    """

    if decision.recommendation == "HOLD":
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="HOLD",
            dry_run=decision.dry_run,
            approved=False,
            reason="Decision was HOLD. No order created.",
        )

    if decision.confidence < MIN_CONFIDENCE:
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason=(
                f"Confidence {decision.confidence:.2f} is below minimum "
                f"threshold {MIN_CONFIDENCE:.2f}."
            ),
        )

    if abs(decision.edge) < MIN_EDGE:
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason=(
                f"Edge {decision.edge:.2%} is below minimum "
                f"threshold {MIN_EDGE:.2%}."
            ),
        )

    if not decision.ticker.strip():
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason="Missing ticker.",
        )

    if not 0 < decision.current_yes_price < 1:
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason="Invalid current_yes_price. Must be between 0 and 1.",
        )

    max_dollars = min(decision.max_order_dollars, MAX_ORDER_DOLLARS)

    contracts = math.floor(max_dollars / decision.current_yes_price)
    contracts = max(1, min(contracts, MAX_CONTRACTS))

    if decision.recommendation == "YES":
        side = "bid"
        action_taken = "BUY_YES"
    elif decision.recommendation == "NO":
        # Kalshi V2 orders are quoted from the YES side.
        # "ask" means sell YES, which is economically similar to taking the NO side.
        side = "ask"
        action_taken = "BUY_NO"
    else:
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason=f"Invalid recommendation: {decision.recommendation}",
        )

    order_payload = {
        "ticker": decision.ticker,
        "client_order_id": str(uuid.uuid4()),
        "side": side,
        "count": str(contracts),
        "price": f"{decision.current_yes_price:.4f}",
        "time_in_force": "good_till_canceled",
        "self_trade_prevention_type": "taker_at_cross",
        "post_only": False,
        "cancel_order_on_pause": True,
        "reduce_only": False,
    }

    return ExecutionResult(
        ticker=decision.ticker,
        action_taken=action_taken,
        dry_run=decision.dry_run,
        approved=True,
        reason="Order passed executor risk checks.",
        order_payload=order_payload,
        estimated_contracts=contracts,
        estimated_cost_dollars=round(contracts * decision.current_yes_price, 2),
    )


def load_private_key():
    """
    Loads your Kalshi private key from disk.

    Do not commit the key file.
    Store only the path in .env as KALSHI_PRIVATE_KEY_PATH.
    """

    if not KALSHI_PRIVATE_KEY_PATH:
        raise RuntimeError("Missing KALSHI_PRIVATE_KEY_PATH")

    with open(KALSHI_PRIVATE_KEY_PATH, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )


def create_signature(private_key, timestamp: str, method: str, path: str) -> str:
    """
    Creates Kalshi RSA-PSS signature.

    Signed message format:
        timestamp + HTTP_METHOD + path_without_query
    """

    path_without_query = path.split("?")[0]
    message = f"{timestamp}{method.upper()}{path_without_query}".encode("utf-8")

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )

    return base64.b64encode(signature).decode("utf-8")


def kalshi_post(path: str, payload: dict) -> dict:
    """
    Sends an authenticated POST request to Kalshi.
    Only called when dry_run=False and ALLOW_LIVE_TRADING=true.
    """

    if not KALSHI_API_KEY:
        raise RuntimeError("Missing KALSHI_API_KEY")

    private_key = load_private_key()

    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))

    full_url = KALSHI_BASE_URL + path
    sign_path = urlparse(full_url).path

    signature = create_signature(
        private_key=private_key,
        timestamp=timestamp,
        method="POST",
        path=sign_path,
    )

    headers = {
        "Content-Type": "application/json",
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }

    response = requests.post(
        full_url,
        headers=headers,
        json=payload,
        timeout=15,
    )

    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}

    if response.status_code >= 400:
        raise RuntimeError(
            f"Kalshi API error {response.status_code}: {json.dumps(body)}"
        )

    return body


def execute_decision(decision: TradeDecision) -> ExecutionResult:
    """
    Main entrypoint used by the uAgent.

    dry_run=True:
        Validate and return order payload only.

    dry_run=False:
        Requires ALLOW_LIVE_TRADING=true.
        Then submits the order to Kalshi.
    """

    result = build_order_from_decision(decision)

    if not result.approved:
        return result

    if decision.dry_run:
        result.reason = "Dry run only. Order was validated but not submitted."
        return result

    allow_live = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"

    if not allow_live:
        return ExecutionResult(
            ticker=decision.ticker,
            action_taken="REJECTED",
            dry_run=decision.dry_run,
            approved=False,
            reason=(
                "Live trading disabled. Set ALLOW_LIVE_TRADING=true "
                "to submit real orders."
            ),
            order_payload=result.order_payload,
            estimated_contracts=result.estimated_contracts,
            estimated_cost_dollars=result.estimated_cost_dollars,
        )

    kalshi_response = kalshi_post(
        "/portfolio/events/orders",
        result.order_payload,
    )

    result.kalshi_response = kalshi_response
    result.reason = "Live order submitted to Kalshi."

    return result