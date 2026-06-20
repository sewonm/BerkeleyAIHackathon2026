"""
Shared output contract for the three research agents (sports, web, financial).
Import this in every research agent and in the compression / coordinator / decision agents.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Per-agent evidence payloads
# Each agent fills in only its own evidence type. Keeping these distinct
# (instead of one big `raw_evidence: str`) lets the compression agent treat
# prose, odds tables, and orderbooks differently instead of guessing.
# ---------------------------------------------------------------------------

class SportsEvidence(BaseModel):
    event_name: str                      # e.g. "Lakers vs Celtics"
    odds_snapshot: str                    # current odds/line as text, e.g. "Lakers -4.5"
    odds_movement: Optional[str] = None   # e.g. "moved from -2.5 to -4.5 in 1hr"
    injury_notes: Optional[str] = None
    raw_text: str                         # fallback: any unstructured detail not captured above


class WebEvidence(BaseModel):
    headline: str
    excerpt: str                          # the compressed/extracted relevant snippet, NOT full page
    source_name: str                      # e.g. "Reuters", "AP"
    published_at: Optional[str] = None    # ISO string if known
    raw_text: str                         # fallback: full or near-full scrape, pre-compression


class FinancialEvidence(BaseModel):
    market_id: str
    last_price: float                     # current Kalshi market price (probability, 0-1 or cents)
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    orderbook_summary: Optional[str] = None   # short text summary, not full depth dump
    raw_text: str                         # fallback: any unstructured detail


# ---------------------------------------------------------------------------
# The actual message each research agent emits
# ---------------------------------------------------------------------------

class ResearchOutput(BaseModel):
    agent: Literal["sports", "web", "financial"]
    market_id: str                        # which Kalshi market this signal is about

    applicable: bool = True               # False if this agent has nothing useful to say
                                           # for this market (e.g. web agent on a pure
                                           # weather market) — lets decision agent skip it
                                           # cleanly instead of treating 0.0 as a real signal

    evidence: SportsEvidence | WebEvidence | FinancialEvidence

    signal: float = Field(ge=-1.0, le=1.0)
    # direction + strength of the signal: -1 = strongly against "yes",
    # +1 = strongly for "yes", 0 = neutral/no opinion

    data_confidence: float = Field(ge=0.0, le=1.0)
    # how much do we trust the underlying data itself (source quality,
    # completeness, freshness of the scrape) — NOT the same as signal strength

    reasoning_confidence: float = Field(ge=0.0, le=1.0)
    # how confident the agent's LLM reasoning is in the signal direction,
    # given the evidence it has

    sources: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    reasoning: str = ""                   # 1-2 sentence explanation, useful for demo + debugging