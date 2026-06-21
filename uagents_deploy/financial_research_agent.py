"""
FinancialResearchAgent — Fully self-contained uAgent for Agentverse deployment.

Fetches live Kalshi market data (price, volume, orderbook) and returns
EvidenceChunks to the orchestrator. No external app/ imports.

Required secrets (set in Agentverse dashboard or local .env):
    KALSHI_API_KEY_ID    — key ID from Kalshi dashboard
    KALSHI_PRIVATE_KEY   — full PEM content with literal \\n between lines
    KALSHI_ENV           — "demo" or "production" (default: demo)

Optional:
    FINANCIAL_AGENT_SEED — deterministic seed for consistent agent address
"""

import os
import base64
import time
from datetime import datetime, timezone
from typing import Optional, List, Literal
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from pydantic import BaseModel, Field
from uagents import Agent, Context, Protocol

# ---------------------------------------------------------------------------
# Inlined message models (no protocols/ folder needed on Agentverse)
# ---------------------------------------------------------------------------

class EvidenceRequest(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    market_question: str
    market_id: Optional[str] = None
    category: str
    protected_terms: List[str] = Field(default_factory=list)


class EvidenceChunkMsg(BaseModel):
    source_type: Literal[
        "culture_web", "sports_video", "politics_news",
        "financial_research", "market", "manual"
    ]
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: dict = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    agent_name: str
    evidence_chunks: List[EvidenceChunkMsg]
    total_chunks: int


class AgentStatus(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    status: Literal["ready", "processing", "completed", "error"]
    message: str

# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------

AGENT_NAME = "financial_research_agent"
AGENT_SEED = os.getenv("FINANCIAL_AGENT_SEED", "financial_research_agent_seed_change_in_production")
AGENT_PORT = 8006

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,
)

evidence_protocol = Protocol("EvidenceCollection")

# ---------------------------------------------------------------------------
# Kalshi API (inlined — no app/ imports needed)
# ---------------------------------------------------------------------------

PROD_BASE = "https://trading-api.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"

_BASE_URL = PROD_BASE if os.getenv("KALSHI_ENV") == "production" else DEMO_BASE
_private_key_cache = None


def _load_private_key():
    global _private_key_cache
    if _private_key_cache is not None:
        return _private_key_cache

    # Agentverse: set KALSHI_PRIVATE_KEY with \\n between PEM lines
    pem = os.getenv("KALSHI_PRIVATE_KEY", "").replace("\\n", "\n").encode()

    if not pem:
        raise ValueError("Set KALSHI_PRIVATE_KEY secret in Agentverse (inline PEM with \\n)")

    _private_key_cache = serialization.load_pem_private_key(
        pem, password=None, backend=default_backend()
    )
    return _private_key_cache


def _auth_headers(method: str, path: str) -> dict:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    if not key_id:
        raise ValueError("Set KALSHI_API_KEY_ID secret in Agentverse")

    key = _load_private_key()
    timestamp_ms = str(int(time.time() * 1000))
    message = (timestamp_ms + method.upper() + path).encode("utf-8")
    signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())

    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "Content-Type": "application/json",
    }


async def kalshi_get_market(market_id: str) -> dict:
    path = f"/trade-api/v2/markets/{market_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{_BASE_URL}/markets/{market_id}", headers=_auth_headers("GET", path))
    r.raise_for_status()
    return r.json()["market"]


async def kalshi_get_orderbook(market_id: str, depth: int = 5) -> dict:
    path = f"/trade-api/v2/markets/{market_id}/orderbook"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{_BASE_URL}/markets/{market_id}/orderbook",
            headers=_auth_headers("GET", path),
            params={"depth": depth},
        )
    r.raise_for_status()
    return r.json().get("orderbook", {})

# ---------------------------------------------------------------------------
# Evidence builders
# ---------------------------------------------------------------------------

def _market_chunk(market_id: str, market_question: str, raw: dict) -> EvidenceChunkMsg:
    now = datetime.now(timezone.utc).isoformat()

    yes_ask = float(raw.get("yes_ask_dollars") or 0)
    yes_bid = float(raw.get("yes_bid_dollars") or 0)
    yes_mid = (yes_ask + yes_bid) / 2 if (yes_ask + yes_bid) > 0 else 0.0

    prev_ask = float(raw.get("previous_yes_ask_dollars") or 0)
    prev_bid = float(raw.get("previous_yes_bid_dollars") or 0)
    prev_mid = (prev_ask + prev_bid) / 2

    price_change_str = f"{((yes_mid - prev_mid) / prev_mid * 100):+.2f}%" if prev_mid > 0 else "N/A (new market)"

    volume = float(raw.get("volume_fp") or 0)
    open_interest = float(raw.get("open_interest_fp") or 0)

    text = (
        f"=== Kalshi Market Data: {raw.get('title', market_id)} ===\n"
        f"Market ID: {market_id}\n"
        f"Question: {market_question}\n"
        f"YES Ask: ${yes_ask:.2f} | YES Bid: ${yes_bid:.2f} | Mid: ${yes_mid:.2f}\n"
        f"NO Ask:  ${float(raw.get('no_ask_dollars') or 0):.2f} | "
        f"NO Bid: ${float(raw.get('no_bid_dollars') or 0):.2f}\n"
        f"Price Change (recent): {price_change_str}\n"
        f"Volume: {volume:,.2f} contracts | Open Interest: {open_interest:,.2f}\n"
        f"Status: {raw.get('status', 'unknown')} | Closes: {raw.get('close_time', 'unknown')}\n"
    )

    return EvidenceChunkMsg(
        source_type="financial_research",
        text=text,
        source_url=f"https://kalshi.com/markets/{market_id}",
        timestamp=now,
        confidence=1.0,
        metadata={
            "yes_mid": round(yes_mid, 4),
            "yes_ask": yes_ask,
            "yes_bid": yes_bid,
            "volume": volume,
            "status": raw.get("status"),
        },
    )


def _orderbook_chunk(market_id: str, raw_market: dict, ob: dict) -> EvidenceChunkMsg:
    now = datetime.now(timezone.utc).isoformat()

    def fmt(side: list) -> str:
        return ", ".join(f"{p}¢×{q}" for p, q in (side or [])[:5]) or "empty"

    yes_levels = ob.get("yes", [])
    no_levels = ob.get("no", [])
    yes_total = sum(q for _, q in yes_levels)
    no_total = sum(q for _, q in no_levels)
    imbalance = "YES-heavy" if yes_total > no_total else "NO-heavy" if no_total > yes_total else "balanced"

    text = (
        f"=== Kalshi Orderbook: {raw_market.get('title', market_id)} ===\n"
        f"YES bids: {fmt(yes_levels)}\n"
        f"NO bids:  {fmt(no_levels)}\n"
        f"Top-5 YES depth: {yes_total:,} | Top-5 NO depth: {no_total:,}\n"
        f"Orderbook imbalance: {imbalance}\n"
    )

    return EvidenceChunkMsg(
        source_type="financial_research",
        text=text,
        source_url=f"https://kalshi.com/markets/{market_id}",
        timestamp=now,
        confidence=1.0,
        metadata={"yes_depth": yes_total, "no_depth": no_total, "imbalance": imbalance},
    )


def _mock_chunks(market_id: str, market_question: str) -> list[EvidenceChunkMsg]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        EvidenceChunkMsg(
            source_type="financial_research",
            text=(
                f"=== Kalshi Market Data (MOCK): {market_question} ===\n"
                f"Market ID: {market_id}\n"
                f"YES Ask: $0.68 | YES Bid: $0.01 | Mid: $0.35\n"
                f"NO Ask: $0.99 | NO Bid: $0.32\n"
                f"Price Change (recent): N/A (new market)\n"
                f"Volume: 0.00 contracts | Open Interest: 0.00\n"
                f"Status: active\n"
            ),
            timestamp=now,
            confidence=0.0,
            metadata={"mock": True},
        )
    ]

# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------

async def collect_financial_evidence(market_id: str, market_question: str) -> list[EvidenceChunkMsg]:
    if not os.getenv("KALSHI_API_KEY_ID"):
        return _mock_chunks(market_id, market_question)

    raw = await kalshi_get_market(market_id)
    ob = await kalshi_get_orderbook(market_id)
    return [
        _market_chunk(market_id, market_question, raw),
        _orderbook_chunk(market_id, raw, ob),
    ]

# ---------------------------------------------------------------------------
# uAgent message handler
# ---------------------------------------------------------------------------

@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    ctx.logger.info(f"[{AGENT_NAME}] Request from {sender} — {msg.market_question}")

    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Fetching Kalshi data for: {msg.market_question}",
    ))

    market_id = msg.market_id or "UNKNOWN"

    try:
        chunks = await collect_financial_evidence(market_id, msg.market_question)
    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Error: {e}")
        await ctx.send(sender, AgentStatus(agent_name=AGENT_NAME, status="error", message=str(e)))
        return

    try:
        from redis_service import append_claims
        append_claims(market_id, [c.model_dump() for c in chunks])
        ctx.logger.info(f"[{AGENT_NAME}] Wrote {len(chunks)} claims to Redis")
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Redis write skipped: {e}")

    await ctx.send(sender, EvidenceResponse(
        request_id=msg.msg_id,
        agent_name=AGENT_NAME,
        evidence_chunks=chunks,
        total_chunks=len(chunks),
    ))

    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Sent {len(chunks)} Kalshi evidence chunks",
    ))


agent.include(evidence_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] address: {agent.address}")
    ctx.logger.info(f"Kalshi: {'LIVE' if os.getenv('KALSHI_API_KEY_ID') else 'MOCK'}")


if __name__ == "__main__":
    agent.run()
