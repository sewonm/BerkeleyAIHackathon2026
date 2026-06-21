"""
ESPN collection spine (Phase 2).

``collect_espn_evidence(market)`` resolves the sport + event from the registry
(no hardcoded sport), fetches every ESPN source, and returns a normalized
``list[EvidenceChunk]``.

Determinism: pass ``observed_at`` (and a fixtures-backed ``ESPNClient``) to get
byte-stable output across runs — used by tests and the offline demo path. The
live default stamps ``observed_at`` with the current UTC time, but the data
fields and chunk ordering are stable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.evidence import EvidenceChunk
from app.services.espn.client import ESPNClient
from app.services.espn.fetchers import (
    fetch_odds,
    fetch_summary,
    scoreboard_url,
    summary_url,
    odds_url,
)
from app.services.espn import normalize as N
from app.services.espn.registry import SportConfig, resolve_sport, get_sport_config
from app.services.espn.resolver import resolve_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_espn_evidence(
    market,
    *,
    client: Optional[ESPNClient] = None,
    sport: Optional[str] = None,
    observed_at: Optional[str] = None,
) -> List[EvidenceChunk]:
    """Collect normalized ESPN anchor evidence for a market.

    Args:
        market: Market object (or string) used to resolve the sport + event.
        client: ESPNClient (inject a fixtures-backed one for tests/offline).
        sport: force a sport key from the registry (skips keyword resolution).
        observed_at: fixed timestamp for deterministic output (default: now UTC).

    Returns:
        List of EvidenceChunk (possibly empty if ESPN is unreachable). Each
        normalizer is isolated: one failing source never kills the bundle.
    """
    client = client or ESPNClient()
    observed_at = observed_at or _utc_now()
    cfg: SportConfig = get_sport_config(sport) if sport else resolve_sport(market)

    resolved = resolve_event(client, cfg, market)
    if not resolved:
        return []
    event = resolved["event"]
    event_id = resolved["event_id"]
    comp_id = resolved["competition_id"]
    event_name = event.get("name") or event_id

    sb_url = scoreboard_url(cfg)
    sm_url = f"{summary_url(cfg)}?event={event_id}"
    od_url = odds_url(cfg, event_id, comp_id)

    summary = fetch_summary(client, cfg, event_id) or {}
    odds_json = fetch_odds(client, cfg, event_id, comp_id) or {}

    chunks: List[EvidenceChunk] = []

    def _add(fn, *args):
        """Run a normalizer defensively; append its chunk(s) if any."""
        try:
            result = fn(*args)
        except Exception:
            return
        if result is None:
            return
        if isinstance(result, list):
            chunks.extend(c for c in result if c is not None)
        else:
            chunks.append(result)

    # SA-DATA-01 — score/state (from scoreboard event)
    _add(N.normalize_score_state, event, cfg, observed_at, sb_url)
    # SA-DATA-02 — box stats + event log (summary)
    _add(N.normalize_box_stats, summary, cfg, observed_at, sm_url, event_id, event_name)
    _add(N.normalize_event_log, summary, cfg, observed_at, sm_url, event_id, event_name)
    # SA-DATA-03 — odds open/close/current (core API)
    _add(N.normalize_odds, odds_json, cfg, observed_at, od_url, event_id, event_name)
    # SA-DATA-04 — win / implied probability (summary + moneyline)
    _add(N.normalize_win_probability, summary, cfg, observed_at, sm_url, event_id, event_name)
    # SA-DATA-05 — injuries + lineups (summary)
    _add(N.normalize_injuries, summary, cfg, observed_at, sm_url, event_id, event_name)
    _add(N.normalize_lineups, summary, cfg, observed_at, sm_url, event_id, event_name)

    return chunks
