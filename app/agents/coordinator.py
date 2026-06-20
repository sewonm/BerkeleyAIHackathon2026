"""
Coordinator Agent — orchestrates all sub-agents and returns final decision.

FLOW:
  1. Call Browserbase research agent (Node, port 3001) → web claims
  2. Pull Redis context (cached claims + market history)
  3. Merge all claims
  4. Compress claims (Sewon's compression module)
  5. Call decision agent (LLM) with compressed packet only
  6. Store result in Redis
  7. Return full response

OWNED BY: Vepaul
This file is the skeleton. Fill in compression + decision imports when ready.
"""

import requests
from app.services import redis_service

BROWSERBASE_AGENT_URL = "http://localhost:3001/browserbase-research"


# ── Sub-agent callers ──────────────────────────────────────────────────────

def call_browserbase_agent(market_question: str, teams: list[str], sport: str) -> dict:
    """
    Calls the Browserbase research agent (TypeScript, port 3001).
    Returns {"claims": [...], "raw_tokens_total": int, ...}
    Falls back to empty claims if agent is unreachable.
    """
    try:
        response = requests.post(
            BROWSERBASE_AGENT_URL,
            json={"market_question": market_question, "teams": teams, "sport": sport},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[coordinator] Browserbase agent unreachable: {e} — using empty claims")
        return {"claims": [], "raw_tokens_total": 0, "compressed_tokens_total": 0}


def call_video_agent(video_path: str | None, market_question: str) -> dict:
    """Derek's video agent. Returns {"claims": [...]}. Stub until Derek wires it."""
    # TODO: Derek fills this in
    return {"claims": []}


def call_stats_agent(teams: list[str], sport: str) -> dict:
    """Stats/market data agent. Returns {"claims": [...]}. Stub until wired."""
    # TODO: wire to stats JSON or live API
    return {"claims": []}


# ── Redis context retrieval ────────────────────────────────────────────────

def get_redis_context(market_id: str) -> list[dict]:
    """Pull any cached claims already stored for this market."""
    return redis_service.get_claims(market_id)


# ── Main orchestration ────────────────────────────────────────────────────

def run_analysis(
    market_question: str,
    market_price: float,
    teams: list[str],
    sport: str,
    market_id: str,
    video_path: str | None = None,
) -> dict:
    """
    Full pipeline. Called by FastAPI /analyze-market endpoint.

    Returns the final decision JSON including compression metrics.
    """
    print(f"[coordinator] Starting analysis: {market_question}")

    # 1. Store market snapshot in Redis
    redis_service.set_market_snapshot(market_id, {
        "market_id": market_id,
        "question": market_question,
        "yes_price": market_price,
        "implied_probability": market_price,
    })

    # 2. Gather evidence from all agents in parallel (TODO: use asyncio/threads for speed)
    web_result   = call_browserbase_agent(market_question, teams, sport)
    video_result = call_video_agent(video_path, market_question)
    stats_result = call_stats_agent(teams, sport)

    # 3. Merge all claims
    all_claims = (
        web_result.get("claims", [])
        + video_result.get("claims", [])
        + stats_result.get("claims", [])
    )
    raw_tokens_total = sum(c.get("raw_tokens", 0) for c in all_claims)

    # 4. Append to Redis (other agents may have added claims too)
    redis_service.clear_claims(market_id)
    redis_service.append_claims(market_id, all_claims)

    # 5. Compress  ← Sewon fills this in
    # from app.compression.compressor import compress_claims
    # compressed_packet = compress_claims(all_claims, market_question)
    compressed_packet = _mock_compress(all_claims, market_id, raw_tokens_total)
    redis_service.set_compressed(market_id, compressed_packet)

    # 6. Decision agent  ← Sewon / Vepaul fills this in
    # from app.agents.decision_agent import run_decision
    # decision = run_decision(compressed_packet, market_price)
    decision = _mock_decision(compressed_packet, market_price, market_question)
    redis_service.set_decision(market_id, decision)

    print(f"[coordinator] Done — recommendation: {decision['recommendation']}")

    return {
        "market_id": market_id,
        "compression_metrics": {
            "raw_context_tokens": raw_tokens_total,
            "compressed_tokens": compressed_packet["compressed_token_count"],
            "compression_ratio": compressed_packet["compression_ratio"],
            "token_reduction_pct": compressed_packet.get("token_reduction_pct", 0),
        },
        "decision": decision,
    }


# ── Temporary stubs (remove when Sewon wires real compression/decision) ───

def _mock_compress(claims: list[dict], market_id: str, raw_tokens: int) -> dict:
    compressed = max(int(raw_tokens * 0.11), 50)
    top = [c["claim"] for c in claims[:4]]
    return {
        "market_id": market_id,
        "raw_token_count": raw_tokens,
        "compressed_token_count": compressed,
        "compression_ratio": f"{raw_tokens / max(compressed, 1):.2f}x",
        "token_reduction_pct": round((1 - compressed / max(raw_tokens, 1)) * 100, 1),
        "top_claims": top,
        "uncertainties": ["Compression is mocked — replace with Sewon's real compressor."],
    }


def _mock_decision(packet: dict, market_price: float, question: str) -> dict:
    estimated_prob = min(market_price + 0.09, 0.95)
    edge = round(estimated_prob - market_price, 3)
    rec = "YES" if edge > 0.07 else ("NO" if edge < -0.07 else "HOLD")
    return {
        "market": question,
        "estimated_probability": estimated_prob,
        "market_probability": market_price,
        "edge": edge,
        "recommendation": rec,
        "confidence": "medium",
        "reasoning": packet.get("top_claims", ["No evidence available."]),
        "risks": packet.get("uncertainties", []),
        "disclaimer": "Simulated research tool. Not financial advice.",
    }
