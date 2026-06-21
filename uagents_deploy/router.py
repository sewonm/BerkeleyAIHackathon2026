"""
router.py — Pure, importable, never-raising routing module for the Quorum multi-agent pipeline.

Design contract (mirrors sports_evidence.py):
- BLOCKING: route() is synchronous; callers wrap in asyncio.to_thread().
- Zero uAgents imports: importable without constructing a uAgent / touching the network.
- Never raises: every rung of the three-tier ladder catches exceptions; route() always
  returns a RouterDecision.
- Import-safe: all app/SDK imports are guarded by try/except at module scope so that
  `import uagents_deploy.router` succeeds with no key, no uAgents, no OpenAI SDK.

Three-rung never-fail ladder:
  Rung 1: LLM tier (_route_llm)       — stub in this plan; plan 02 implements it
  Rung 2: Scored-keyword heuristic    — this plan's deliverable (_route_heuristic)
  Rung 3: Safe culture default        — last-resort (_route_default)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level guarded LLMService import.
# PATCHABILITY: `LLMService` must exist as a module-level name so that plan 02's
# tests can do `patch("uagents_deploy.router.LLMService", ...)`.
# A purely function-local import does NOT create this attribute.
# ---------------------------------------------------------------------------
try:
    from app.services.llm_service import LLMService  # noqa: F401 — exposed for test patching
    LLM_IMPORTABLE = True
except Exception:                                     # never raises at import (TEST-01)
    LLMService = None        # type: ignore
    LLM_IMPORTABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset({"sports", "financial", "culture", "politics", "none"})

CATEGORY_TO_AGENT: dict[str, Optional[str]] = {
    "sports":    "sports_video",
    "financial": "financial_research",
    "culture":   "culture_web",
    "politics":  None,   # routable decision; no deployed agent yet
    "none":      None,
}

REJECT_FLOOR = 0.35   # below this confidence -> category="none"
AUTO_FLOOR   = 0.65   # above this: action="auto_route" (Phase 4)

# ---------------------------------------------------------------------------
# RouterDecision dataclass
# Pure, in-process only — never goes on the wire.
# Phase 3 unpacks it into the existing EvidenceRequest.
# ---------------------------------------------------------------------------

@dataclass
class RouterDecision:
    category: str                    # one of VALID_CATEGORIES
    target_agent_key: Optional[str]  # CATEGORY_TO_AGENT[category]; None for politics/none
    rewritten_query: str             # -> EvidenceRequest.market_question
    protected_terms: list[str]       # verbatim entities + years -> EvidenceRequest.protected_terms
    confidence: float                # 0-1
    rationale: str                   # one-sentence; surfaced to user in plan 03
    tier: str                        # "llm" | "heuristic" | "default" (provenance)


# ---------------------------------------------------------------------------
# Keyword weight tables — the headline SAFETY-02 bug fix.
# Tuned against the 14 worked examples in 02-RESEARCH.md.
# Do NOT retune here — Phase 4 owns calibration.
#
# Key invariants:
#   "world cup"=3.0(sports)  |  "bitcoin"=4.0(financial)
#   "election"/"senate"/"congress"=4.0(politics)
#   "government shutdown"=4.0 / "shutdown"=3.0(politics)
#   "win"=0.5(sports, deliberately weak so financial/politics beat it)
# ---------------------------------------------------------------------------

_KEYWORD_WEIGHTS: dict[str, dict[str, float]] = {
    "sports": {
        # Strong / unambiguous
        "nba": 3.0, "nfl": 3.0, "mlb": 3.0, "nhl": 3.0, "fifa": 3.0,
        "world cup": 3.0, "super bowl": 3.0, "olympics": 3.0,
        "lakers": 3.0, "celtics": 3.0, "chiefs": 3.0, "patriots": 3.0,
        "yankees": 3.0, "dodgers": 3.0,
        "soccer": 2.5, "basketball": 2.5, "baseball": 2.5, "hockey": 2.5,
        "tennis": 2.5, "football": 2.0,
        # Moderate
        "champion": 2.0, "game": 1.5, "match": 1.5, "score": 1.5,
        "team": 1.5, "player": 1.5, "season": 1.5, "league": 1.5,
        "playoff": 2.0, "finals": 2.0, "tournament": 2.0,
        # Weak / ambiguous — low weight so financial/politics can beat them
        "win": 0.5, "beat": 0.5, "defeat": 0.5,
    },
    "financial": {
        # Strong / unambiguous
        "bitcoin": 4.0, "btc": 4.0, "ethereum": 3.5, "eth": 3.0,
        "crypto": 3.0, "s&p": 3.5, "sp500": 3.5, "nasdaq": 3.5,
        "dow": 3.0, "stock": 3.0, "etf": 3.0,
        # Moderate
        "price": 2.0, "dollar": 2.0, "usd": 2.0, "trading": 2.0,
        "interest rate": 3.0, "fed": 2.5, "inflation": 2.5,
        "market cap": 3.0, "ipo": 3.0, "earnings": 2.5,
        # Ambiguous but lean financial
        "$": 1.5, "100k": 1.5, "k by": 1.0,
        # Very weak / shared with other categories
        "market": 0.5,
    },
    "culture": {
        "oscar": 3.0, "grammy": 3.0, "emmy": 3.0, "academy award": 3.0,
        "box office": 2.5, "film": 2.0, "movie": 2.0, "album": 2.5,
        "song": 2.0, "artist": 1.5, "celebrity": 2.0, "actor": 2.0,
        "actress": 2.0, "director": 2.0, "concert": 2.0, "tour": 1.5,
        "book": 1.5, "award": 2.0, "nomination": 2.0,
        "taylor swift": 3.0, "oppenheimer": 2.5,
    },
    "politics": {
        # Strong / unambiguous — these must beat sports-adjacent "win"
        "election": 4.0, "senate": 4.0, "congress": 4.0, "president": 4.0,
        "governor": 4.0, "parliament": 4.0, "legislation": 3.5,
        "government shutdown": 4.0, "shutdown": 3.0,
        "midterm": 4.0, "primary": 3.0, "ballot": 3.5, "vote": 3.0,
        "incumbent": 3.5, "party": 2.5, "democrat": 4.0, "republican": 4.0,
        "supreme court": 4.0, "bill": 2.0, "law": 2.0, "policy": 2.5,
        "tariff": 3.0, "sanction": 3.0, "treaty": 3.0,
        # Moderate
        "federal": 2.5, "state": 1.5, "mayor": 3.0, "referendum": 3.5,
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def route(question: str) -> RouterDecision:
    """Single public entry. BLOCKING (caller wraps in asyncio.to_thread). Never raises."""
    q = (question or "").strip()
    if not q:
        return _route_default("", reason="empty question")

    # Rung 1: LLM tier (stub in plan 01; plan 02 implements the real call)
    try:
        decision = _route_llm(q)
        if decision is not None:
            logger.info(
                "[router] tier=llm category=%s conf=%.2f",
                decision.category, decision.confidence,
            )
            return decision
    except Exception as exc:
        logger.warning(
            "[router] LLM tier error: %s — falling back to heuristic",
            type(exc).__name__,
        )

    # Rung 2: Scored-keyword heuristic (always available, no network)
    try:
        decision = _route_heuristic(q)
        logger.info(
            "[router] tier=heuristic category=%s conf=%.2f",
            decision.category, decision.confidence,
        )
        return decision
    except Exception as exc:
        logger.warning(
            "[router] Heuristic tier error: %s — using safe default",
            type(exc).__name__,
        )

    # Rung 3: Safe default (culture, never fails)
    return _route_default(q, reason="all tiers failed")


# ---------------------------------------------------------------------------
# Private tier implementations
# ---------------------------------------------------------------------------

def _route_llm(question: str) -> Optional[RouterDecision]:
    """Rung 1 — LLM tier. Stub in plan 01; real impl in plan 02. Returns None -> falls to heuristic."""
    return None


def _route_heuristic(question: str) -> RouterDecision:
    """
    Rung 2 — Scored-keyword classifier. Returns RouterDecision with tier="heuristic".
    NEVER raises — all logic is pure string matching and arithmetic.

    Scoring contract:
    - lower-case the question
    - for each (category, kw, weight): if kw in q_lower: scores[cat] += weight
    - total = sum(scores); if total==0.0 -> category="none", confidence=0.0
    - best_cat = max by score; confidence = scores[best]/total
    - if confidence < REJECT_FLOOR OR scores[best] < 1.0 -> category="none"
    """
    q_lower = question.lower()
    scores: dict[str, float] = {cat: 0.0 for cat in _KEYWORD_WEIGHTS}

    for category, keywords in _KEYWORD_WEIGHTS.items():
        for kw, weight in keywords.items():
            if kw in q_lower:
                scores[category] += weight

    total = sum(scores.values())

    if total == 0.0:
        # No keywords matched — OOD or unrecognizable
        return RouterDecision(
            category="none",
            target_agent_key=None,
            rewritten_query=question,
            protected_terms=_extract_years(question),
            confidence=0.0,
            rationale="No recognizable category keywords found",
            tier="heuristic",
        )

    # Winner: highest score
    best_cat = max(scores, key=lambda c: scores[c])
    confidence = scores[best_cat] / total

    # OOD reject floor: low confidence OR absolute score too weak
    if confidence < REJECT_FLOOR or scores[best_cat] < 1.0:
        best_cat = "none"

    rationale = (
        f"Keyword scoring: {best_cat} scored {scores.get(best_cat, 0):.1f}"
        f" of {total:.1f} total ({confidence:.0%})"
    )

    return RouterDecision(
        category=best_cat,
        target_agent_key=CATEGORY_TO_AGENT.get(best_cat),
        rewritten_query=question,   # heuristic tier: forward raw (no LLM rewrite)
        protected_terms=_extract_years(question),
        confidence=round(confidence, 3),
        rationale=rationale,
        tier="heuristic",
    )


def _route_default(question: str, reason: str = "") -> RouterDecision:
    """Rung 3 — safe culture default. Never fails."""
    return RouterDecision(
        category="culture",
        target_agent_key=CATEGORY_TO_AGENT["culture"],
        rewritten_query=question,
        protected_terms=_extract_years(question),
        confidence=0.1,
        rationale=f"Safe default (culture): {reason}",
        tier="default",
    )


def _extract_years(text: str) -> list[str]:
    """Extract 4-digit years (20xx) as protected terms. Dedup, order-preserving."""
    return list(dict.fromkeys(re.findall(r'\b(20\d{2})\b', text)))
