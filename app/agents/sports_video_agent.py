"""
Sports live-stats evidence agent — SYNC core.

This module provides the sync SportsAgent used by the coordinator. It is the
SYNC counterpart to the deployed uAgent (uagents_deploy/sports_video_agent.py).
It does NOT import uagents; it is a plain BaseAgent subclass.

Phase 2 (this implementation): ``run()`` pulls live, deterministic data from the
free ESPN HTTP JSON APIs for ANY sport (via the sport->source registry) and emits
normalized ``EvidenceChunk``s. It falls back to a hardcoded stub bundle if ESPN is
unreachable, so the coordinator contract (>= 2 chunks) always holds and the demo
survives offline. Set ``SPORTS_AGENT_OFFLINE=1`` to force the stub path.

Phase 3 adds the Browserbase noisy layer; Phase 4 merges anchor + noisy into one
query-aware bundle.

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

def _offline() -> bool:
    """True when the stub path is forced via ``SPORTS_AGENT_OFFLINE``."""
    return os.getenv("SPORTS_AGENT_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


class SportsAgent(BaseAgent):
    """
    Gathers raw sports evidence from live stats sources.

    Phase 2 (this implementation): ``run()`` resolves the sport/league + game from
    the registry and pulls live ESPN HTTP data (score/state, box stats, event log,
    odds with line movement, win/implied probability, injuries, lineups), each
    normalized to an ``EvidenceChunk``. If ESPN is unreachable (or
    ``SPORTS_AGENT_OFFLINE`` is set) it returns a hardcoded stub bundle so the
    pipeline never breaks.

    Constructible with NO args (the coordinator calls ``SportsVideoAgent()``).
    ``run()`` is SYNCHRONOUS — no async, no uagents imports here.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SportsAgent",
            description="Gathers raw sports evidence (ESPN HTTP anchor)",
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """Collect sports evidence for a market — live ESPN, stub fallback.

        Args:
            market: The prediction market to research. Its sport/league + game
                    are resolved from the registry (no hardcoded sport).

        Returns:
            List of >= 2 ``EvidenceChunk`` objects with
            ``source_type="sports_video"`` and the four standardised metadata
            keys ``kind``, ``fetched_via``, ``source_strength``, ``observed_at``
            (live chunks add ``sport``, ``league``, ``event_id``).
        """
        observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        title = market.title or "the market"

        if not _offline():
            chunks = self._collect_live(market, observed_at)
            if len(chunks) >= 2:
                return chunks

        return self._build_stub_bundle(title=title, observed_at=observed_at)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_live(market: Market, observed_at: str) -> List[EvidenceChunk]:
        """Pull the merged sports bundle (ESPN anchor + Browserbase noisy).

        Never raises — returns [] on failure. Lazy import keeps the agent
        importable even if the data layer or its deps are missing (the
        coordinator depends on this module).
        """
        try:
            from app.services.sports_collector import collect_sports_evidence

            return collect_sports_evidence(market, observed_at=observed_at)
        except Exception:
            return []

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
