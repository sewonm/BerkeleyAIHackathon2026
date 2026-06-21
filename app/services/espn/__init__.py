"""
ESPN HTTP anchor layer (Phase 2).

Pulls comprehensive, deterministic live data from ESPN's free (undocumented)
JSON APIs for ANY sport via a sport->source registry, and normalizes every
source into ``EvidenceChunk`` objects.

Public surface:
    collect_espn_evidence(market, ...) -> list[EvidenceChunk]   # the spine
    ESPNClient                                                   # stubbable HTTP client
    SPORT_REGISTRY, resolve_sport, get_sport_config             # config-only sports

Design rules:
- Sport-agnostic: a new sport is a new ``SPORT_REGISTRY`` entry, no pipeline edits
  (SA-DATA-06).
- Defensive: ESPN APIs are undocumented, so every parse is wrapped in try/except;
  a shape change drops that one chunk, it never crashes the bundle.
- Deterministic & offline-safe: ``ESPNClient`` can read recorded fixtures so tests
  are byte-stable and the demo survives with the network off (seeds Phase 5).
"""

from app.services.espn.registry import (
    SPORT_REGISTRY,
    SportConfig,
    ScrapeTarget,
    resolve_sport,
    get_sport_config,
)
from app.services.espn.client import ESPNClient
from app.services.espn.collector import collect_espn_evidence

__all__ = [
    "SPORT_REGISTRY",
    "SportConfig",
    "ScrapeTarget",
    "resolve_sport",
    "get_sport_config",
    "ESPNClient",
    "collect_espn_evidence",
]
