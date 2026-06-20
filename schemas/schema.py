"""
Shared message contracts for the multi-agent trading pipeline.

Pipeline flow:
    Coordinator
        → Research Agents (sports, web, financial)  →  ResearchOutput
        → Compression Agent (all outputs at once)   →  CompressedPacket
        → Decision Agent (calls Claude)             →  TradeDecision
        → Kalshi trade execution

Import this in every agent. Do not define message schemas anywhere else.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Per-agent raw evidence payloads
# Research agents populate only their own evidence type.
# Keeping these distinct lets the compression agent treat each source
# differently rather than flattening everything into one blob.
# ---------------------------------------------------------------------------

class SportsEvidence(BaseModel):
    event_name: str
    odds_snapshot: str                  # e.g. "Lakers -4.5"
    odds_movement: Optional[str] = None # e.g. "moved from -2.5 to -4.5 in 1hr"
    injury_notes: Optional[str] = None
    raw_text: str                       # any unstructured detail not captured above


class WebEvidence(BaseModel):
    headline: str
    excerpt: str                        # relevant snippet extracted from page, NOT full HTML
    source_name: str                    # e.g. "Reuters", "AP"
    published_at: Optional[str] = None  # ISO string if known
    raw_text: str                       # full or near-full scrape, pre-compression


class FinancialEvidence(BaseModel):
    market_id: str
    last_price: float                         # YES probability (0.0–1.0)
    price_change_pct: Optional[float] = None
    volume: Optional[int] = None
    orderbook_summary: Optional[str] = None   # short text summary of top orderbook levels
    raw_text: str                             # any unstructured detail


# ---------------------------------------------------------------------------
# ResearchOutput — emitted by each research agent
# Raw data only. No LLM reasoning, no signal. That lives in the decision agent.
# ---------------------------------------------------------------------------

class ResearchOutput(BaseModel):
    agent: Literal["sports", "web", "financial"]
    market_id: str

    applicable: bool = True
    # Set False when this agent has nothing useful to say about this market
    # (e.g. sports agent on a Fed rate decision). Compression + decision agents
    # should skip non-applicable outputs rather than treating them as neutral.

    evidence: SportsEvidence | WebEvidence | FinancialEvidence

    data_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    # Freshness + completeness of the raw data (not a signal strength).
    # 1.0 = live, complete data. 0.0 = stale, partial, or fetch failed.
    # The compression agent uses this to weight sources.

    sources: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# CompressionInput — sent TO the compression agent
# Aggregates all research outputs for a single market in one message.
#
# To compress individually instead of all-at-once:
#   change `research_outputs: list[ResearchOutput]`
#   to     `research_output: ResearchOutput`
#   and call the compression agent once per research agent.
# ---------------------------------------------------------------------------

class CompressionInput(BaseModel):
    market_id: str
    research_outputs: list[ResearchOutput]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# CompressedPacket — emitted by the compression agent, consumed by decision agent
# ---------------------------------------------------------------------------

class CompressedPacket(BaseModel):
    market_id: str
    compressed_evidence: str    # dense text ready to be injected into Claude's prompt
    original_sources: list[str] # union of all sources across research agents
    compression_ratio: float    # (original token count) / (compressed token count), for telemetry
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# TradeDecision — emitted by the decision agent after Claude reasoning
# ---------------------------------------------------------------------------

class TradeDecision(BaseModel):
    market_id: str
    action: Literal["yes", "no", "hold"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str              # Claude's one-sentence justification
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
