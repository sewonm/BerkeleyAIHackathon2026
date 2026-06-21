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
# Public entry point — stub (RED phase, Task 1)
# ---------------------------------------------------------------------------

def route(question: str) -> RouterDecision:
    """Single public entry. BLOCKING (caller wraps in asyncio.to_thread). Never raises."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Private tier stubs
# ---------------------------------------------------------------------------

def _route_llm(question: str) -> Optional[RouterDecision]:
    """Rung 1 — LLM tier. Stub in plan 01; real impl in plan 02. Returns None -> falls to heuristic."""
    return None


def _route_heuristic(question: str) -> RouterDecision:
    """Rung 2 — Scored-keyword heuristic. Stub in RED phase."""
    raise NotImplementedError


def _route_default(question: str, reason: str = "") -> RouterDecision:
    """Rung 3 — Safe culture default. Stub in RED phase."""
    raise NotImplementedError


def _extract_years(text: str) -> list[str]:
    """Extract 4-digit years (20xx) as protected terms. Stub in RED phase."""
    raise NotImplementedError
