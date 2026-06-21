"""
Path A bridge — HTTP API between the Next.js frontend and the live research agents.

The frontend speaks browser HTTP; the deployed agents speak the uAgents messaging
protocol, which a browser can't call directly. Rather than route through the
orchestrator + mailbox (Path B), this bridge imports the SAME live collector code
the deployed agents use and exposes it over plain JSON HTTP:

    POST /analyze  { question, ticker, category, yesPrice }
      -> routes to the live collector for the category (culture / sports / financial)
      -> converts the raw EvidenceChunk bundle
      -> runs the REAL compression layer (app.compression.Compressor)
      -> returns per-agent breakdown + compression metrics + a decision summary
         in the shape the frontend's AnalysisResult already expects.

This is intentionally the "fast path": real evidence + real compression today,
without waiting on the full orchestrator/decision/execution wiring. The decision
here is a transparent heuristic (no LLM) — swap in the real decision agent later.

Run:
    uvicorn app.bridge_server:app --reload --port 8080
    # (from the repo root, with the same .env that powers the agents)
"""

from __future__ import annotations

import os
import sys
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- make both the repo root and uagents_deploy importable -----------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UAGENTS_DIR = os.path.join(REPO_ROOT, "uagents_deploy")
for p in (REPO_ROOT, UAGENTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env so the live collectors see SERPER/BROWSERBASE/KALSHI keys.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(REPO_ROOT, ".env"))
except Exception:
    pass

# --- real compression layer + schemas --------------------------------------
from app.compression.compressor import Compressor
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.utils.token_counter import count_tokens

# --- live collectors (same code the deployed agents run) -------------------
# Each guarded so one bad import doesn't take down the whole bridge.
try:
    from culture_evidence import collect_bundle as culture_collect  # async
    _CULTURE_OK = True
except Exception as e:  # pragma: no cover
    _CULTURE_OK, _CULTURE_ERR = False, e

try:
    from sports_evidence import collect_bundle as sports_collect  # sync
    _SPORTS_OK = True
except Exception as e:  # pragma: no cover
    _SPORTS_OK, _SPORTS_ERR = False, e

try:
    from financial_research_agent import collect_financial_evidence as financial_collect  # async
    _FINANCIAL_OK = True
except Exception as e:  # pragma: no cover
    _FINANCIAL_OK, _FINANCIAL_ERR = False, e


# ---------------------------------------------------------------------------
# Agent registry (label/icon match the frontend's PipelineView cards)
# ---------------------------------------------------------------------------

AGENT_META = {
    "financial": {"id": "financial", "label": "Financial Research Agent", "icon": "📈"},
    "culture":   {"id": "culture",   "label": "Culture Web Agent",        "icon": "🌐"},
    "sports":    {"id": "sports",    "label": "Sports Video Agent",       "icon": "⚽"},
}

compressor = Compressor()

app = FastAPI(title="Quorum Path A Bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the frontend origin for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    question: str
    ticker: str = ""
    category: str = "culture"
    yesPrice: float = 0.5


# ---------------------------------------------------------------------------
# Collection: route to the live collector(s) for the category
# ---------------------------------------------------------------------------

_SPORTS_KEYWORDS = ("nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball",
                    "baseball", "hockey", "world cup", "playoff", "finals", "game",
                    "match", "lakers", "yankees", "win the", "beat", "cover the spread")
_FINANCIAL_KEYWORDS = ("fed", "rate", "rates", "interest", "inflation", "gdp", "stock",
                       "kalshi", "price", "above", "below", "temp", "temperature", "cpi")


def detect_category(question: str) -> str:
    """Lightweight category routing for custom questions (category='auto')."""
    q = (question or "").lower()
    if any(k in q for k in _SPORTS_KEYWORDS):
        return "sports"
    if any(k in q for k in _FINANCIAL_KEYWORDS):
        return "financial"
    return "culture"


async def _collect_for(category: str, question: str, ticker: str) -> dict[str, list]:
    """Return {agent_id: [EvidenceChunkMsg, ...]} for the given category.

    Culture runs for every market (web search works for any topic). The
    category's primary agent runs in addition when it differs.
    """
    cat = (category or "culture").lower()
    if cat in ("auto", "", "custom"):
        cat = detect_category(question)
    tasks: dict[str, "asyncio.Future"] = {}

    async def _run_culture():
        msgs, _meta = await culture_collect(question)
        return msgs

    async def _run_sports():
        # sports collect_bundle is blocking -> off the event loop
        msgs, _meta = await asyncio.to_thread(sports_collect, question)
        return msgs

    async def _run_financial():
        return await financial_collect(ticker or "UNKNOWN", question)

    if cat == "sports" and _SPORTS_OK:
        tasks["sports"] = asyncio.ensure_future(_run_sports())
    elif cat == "financial" and _FINANCIAL_OK:
        tasks["financial"] = asyncio.ensure_future(_run_financial())

    # Culture always runs as a general web corroborator.
    if _CULTURE_OK:
        tasks["culture"] = asyncio.ensure_future(_run_culture())

    results: dict[str, list] = {}
    for agent_id, fut in tasks.items():
        try:
            results[agent_id] = await fut
        except Exception:
            results[agent_id] = []
    return results


def _to_evidence_chunks(msgs: list) -> list[EvidenceChunk]:
    """Transport EvidenceChunkMsg -> app EvidenceChunk (identical field set)."""
    out = []
    for m in msgs:
        d = m.model_dump() if hasattr(m, "model_dump") else dict(m)
        try:
            out.append(EvidenceChunk(**d))
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Decision heuristic (transparent, no LLM — swap for the real agent later)
# ---------------------------------------------------------------------------

def _heuristic_decision(question: str, yes_price: float, kept_chunks: list, n_chunks: int) -> dict:
    """Derive a YES/NO/HOLD from evidence volume + price. Clearly a placeholder."""
    # More corroborating evidence nudges fair value away from the market price.
    signal = min(n_chunks, 20) / 20.0  # 0..1 evidence strength
    # Centre fair value on the market, widen with evidence (demo heuristic).
    drift = (signal - 0.5) * 0.16
    fair = max(0.01, min(0.99, round(yes_price + drift, 2)))
    edge = round(fair - yes_price, 2)
    confidence = round(0.55 + signal * 0.30, 2)

    if abs(edge) < 0.05:
        rec = "HOLD"
    elif edge > 0:
        rec = "YES"
    else:
        rec = "NO"

    key_evidence = []
    for c in kept_chunks[:4]:
        # kept_chunks are dicts: {"text", "score", "source_type", "source_url"}
        text = (c.get("text") if isinstance(c, dict) else getattr(c, "text", "")) or ""
        first = text.splitlines()[0] if text else ""
        if first:
            key_evidence.append(first[:160])

    return {
        "recommendation": rec,
        "confidence": confidence,
        "fairProbability": fair,
        "yesPrice": yes_price,
        "edge": edge,
        "reasoning": (
            f"Heuristic over {n_chunks} live evidence chunks: evidence strength "
            f"{signal:.0%} implies fair value ${fair:.2f} vs market ${yes_price:.2f} "
            f"(edge {edge:+.2f}). NOTE: placeholder decision — wire the real "
            f"decision agent for LLM reasoning."
        ),
        "keyEvidence": key_evidence or ["No high-signal evidence extracted."],
        "missingInfo": [
            "LLM-based decision agent not yet wired (using heuristic).",
            "Trade execution gated behind the executor agent (Path B).",
        ],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "collectors": {
            "culture": _CULTURE_OK,
            "sports": _SPORTS_OK,
            "financial": _FINANCIAL_OK,
        },
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Full Path A pipeline: live evidence -> real compression -> decision summary."""
    started = datetime.now(timezone.utc)

    # 1) Collect live evidence per agent
    per_agent_msgs = await _collect_for(req.category, req.question, req.ticker)

    # 2) Per-agent breakdown (for the PipelineView cards) + flatten for compression
    agents_out = []
    all_chunks: list[EvidenceChunk] = []
    for agent_id, msgs in per_agent_msgs.items():
        chunks = _to_evidence_chunks(msgs)
        raw_tokens = sum(count_tokens(c.text or "") for c in chunks)
        meta = AGENT_META.get(agent_id, {"id": agent_id, "label": agent_id, "icon": "🔎"})
        # Real evidence samples so the UI can prove the agent actually ran:
        # the live source URL + a snippet from each of the first few chunks.
        sources = []
        for c in chunks[:5]:
            text = (c.text or "").replace("===", "").strip()
            snippet = " ".join(text.split())[:160]
            sources.append({
                "url": c.source_url or "",
                "kind": (c.metadata or {}).get("kind", ""),
                "via": (c.metadata or {}).get("fetched_via", ""),
                "snippet": snippet,
            })
        agents_out.append({
            **meta,
            "status": "done" if chunks else "error",
            "chunks": len(chunks),
            "rawTokens": raw_tokens,
            "sources": sources,
        })
        all_chunks.extend(chunks)

    # 3) Real compression over the combined evidence
    market = Market(
        market_id=req.ticker or "bridge-query",
        title=req.question or "market",
        question=req.question or "market",
        category=req.category or "culture",
        current_yes_price=req.yesPrice,
        resolution_criteria="Resolves per the official market result.",
    )
    comp = compressor.compress(market=market, evidence_chunks=all_chunks, token_budget=3000)

    # 4) Decision summary (heuristic placeholder)
    decision = _heuristic_decision(
        req.question, req.yesPrice, comp.kept_chunks, len(all_chunks)
    )

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    return {
        "market": {"question": req.question, "ticker": req.ticker, "category": req.category},
        "agents": agents_out,
        "rawTokens": comp.raw_token_count,
        "compressedTokens": comp.compressed_token_count,
        "compressionRatio": round(comp.compression_ratio, 2),
        "keptChunks": len(comp.kept_chunks),
        "droppedChunks": len(comp.dropped_chunks),
        "result": {
            **decision,
            "rawTokens": comp.raw_token_count,
            "compressedTokens": comp.compressed_token_count,
            "compressionRatio": round(comp.compression_ratio, 2),
            "riskApproved": decision["confidence"] >= 0.7 and abs(decision["edge"]) >= 0.05,
            "tradeMode": "dry_run",
            "tradeAction": (
                "No trade — HOLD" if decision["recommendation"] == "HOLD"
                else f"Buy {decision['recommendation']} @ ${req.yesPrice:.2f}"
            ),
            "orderSize": 5,
        },
        "elapsedSeconds": round(elapsed, 2),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.bridge_server:app", host="0.0.0.0", port=8080, reload=False)