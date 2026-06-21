"""
Sports live-stats evidence agent — SYNC core (Phase 1: stub bundle).

This module provides the sync SportsAgent used by the coordinator. It is the
SYNC counterpart to the deployed uAgent (uagents_deploy/sports_video_agent.py).
It does NOT import uagents; it is a plain BaseAgent subclass.

Phase 1: Returns a hardcoded stub bundle (no network, no ESPN, no Browserbase).
Phases 2-3 will replace stub with live ESPN data + Browserbase noisy layer.

Seed helper (SA-AGENT-01 groundwork):
    The deployed uAgent's stable identity seed lives here so there is ONE place
    to update it. The deployed agent reads the same env var.
"""

import os
from datetime import datetime, timezone
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.evidence import EvidenceChunk
from app.schemas.market import Market


# ---------------------------------------------------------------------------
# Seed constants (shared with uagents_deploy/sports_video_agent.py via env)
# ---------------------------------------------------------------------------

DEFAULT_SPORTS_AGENT_SEED = "quorum-sports-agent-phase1-seed-v1"


def get_sports_agent_seed() -> str:
    """Return the seed for the deployed sports uAgent.

    Reads ``SPORTS_VIDEO_AGENT_SEED`` env var; falls back to
    ``DEFAULT_SPORTS_AGENT_SEED`` if unset.  The deployed agent uses the same
    env var, so changing the seed in production only requires setting the var.
    """
    return os.getenv("SPORTS_VIDEO_AGENT_SEED", DEFAULT_SPORTS_AGENT_SEED)


# ---------------------------------------------------------------------------
# Sync core agent
# ---------------------------------------------------------------------------

class SportsAgent(BaseAgent):
    """
    Gathers raw sports evidence from live stats sources.

    Phase 1 (this implementation): Returns a hardcoded stub bundle of >= 2
    ``EvidenceChunk`` objects so the coordinator pipeline works end-to-end
    before real data sources are wired up.

    Phase 2 will replace ``_build_stub_bundle`` with live ESPN API calls.
    Phase 3 will add the Browserbase noisy layer on top.

    Constructible with NO args (the coordinator calls ``SportsVideoAgent()``).
    ``run()`` is SYNCHRONOUS — no async, no uagents imports here.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SportsAgent",
            description="Gathers raw sports evidence (Phase 1: stub bundle)",
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """Return a hardcoded stub bundle of sports evidence chunks.

        Args:
            market: The prediction market to research.  The market title is
                    lightly woven into stub text so the bundle looks
                    market-aware, but it works for ANY market.

        Returns:
            List of >= 2 ``EvidenceChunk`` objects with
            ``source_type="sports_video"`` and the four standardised metadata
            keys ``kind``, ``fetched_via``, ``source_strength``, ``observed_at``.
        """
        observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        title = market.title or "the market"

        return self._build_stub_bundle(title=title, observed_at=observed_at)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_stub_bundle(title: str, observed_at: str) -> List[EvidenceChunk]:
        """Build the two-chunk stub bundle for Phase 1.

        Each chunk carries the four standardised metadata keys inside
        ``metadata`` (matching the ``EvidenceChunkMsg`` transport contract in
        ``uagents_deploy/protocols/messages.py``).
        """
        return [
            EvidenceChunk(
                source_type="sports_video",
                text=(
                    f"[STUB] Scoreline related to '{title}': "
                    "Argentina 2-1 Brazil (90', friendly warm-up match, 2026-06-19). "
                    "Argentina dominated possession (62%) and scored twice in the second half."
                ),
                source_url="stub://sports/phase1",
                timestamp=observed_at,
                confidence=0.5,
                metadata={
                    "kind": "scoreline",
                    "fetched_via": "stub",
                    "source_strength": "stub",
                    "observed_at": observed_at,
                },
            ),
            EvidenceChunk(
                source_type="sports_video",
                text=(
                    f"[STUB] Injury report related to '{title}': "
                    "Key Argentina midfielder Enzo Fernandez listed as questionable (hamstring) "
                    "for the tournament opener. Head coach confirms squad otherwise fit."
                ),
                source_url="stub://sports/phase1",
                timestamp=observed_at,
                confidence=0.5,
                metadata={
                    "kind": "injury_report",
                    "fetched_via": "stub",
                    "source_strength": "stub",
                    "observed_at": observed_at,
                },
            ),
        ]


# ---------------------------------------------------------------------------
# Backward-compat alias — coordinator.py imports SportsVideoAgent
# ---------------------------------------------------------------------------

# app/agents/coordinator.py does:
#   from app.agents.sports_video_agent import SportsVideoAgent
#   self.sports_agent = SportsVideoAgent()          # no args
#   self.sports_agent.run(market)                   # synchronous
# This alias keeps that call site unchanged.
SportsVideoAgent = SportsAgent
