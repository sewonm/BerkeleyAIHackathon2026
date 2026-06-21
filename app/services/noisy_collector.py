"""
Noisy evidence collector (Phase 3).

Scrapes RAW text from each of a sport's registry ``scrape_targets`` via the
``BrowserbaseService`` and normalizes them into ``EvidenceChunk``s. This is the
noisy counterpart to the ESPN anchor layer; the two are merged into one
query-aware bundle in Phase 4.

Sport-agnostic: the targets come from the same ``SPORT_REGISTRY`` that drives the
anchor layer, so adding a sport (with its noisy sources) stays config-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.evidence import EvidenceChunk
from app.services.browserbase_service import BrowserbaseService
from app.services.espn.registry import (
    ScrapeTarget,
    SportConfig,
    get_sport_config,
    resolve_sport,
)

NOISY_FETCHED_VIA = "browserbase"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_noisy_chunk(
    text: str, target: ScrapeTarget, cfg: SportConfig, observed_at: str
) -> EvidenceChunk:
    return EvidenceChunk(
        source_type="sports_video",
        text=text.strip(),
        source_url=target.url,
        timestamp=observed_at,
        confidence=0.4,  # noisy: lower trust than the ESPN anchor
        metadata={
            "kind": target.kind,
            "fetched_via": NOISY_FETCHED_VIA,
            "sport": cfg.key,
            "source_strength": target.source_strength,  # "noisy"
            "observed_at": observed_at,
            "label": target.label,
            "league": cfg.espn_league,
        },
    )


def collect_noisy_evidence(
    market,
    *,
    service: Optional[BrowserbaseService] = None,
    sport: Optional[str] = None,
    observed_at: Optional[str] = None,
    max_targets: Optional[int] = None,
) -> List[EvidenceChunk]:
    """Collect raw-text noisy evidence for a market's sport.

    Args:
        market: Market (or string) used to resolve the sport.
        service: BrowserbaseService (inject a fixtures-backed one for tests/offline).
        sport: force a sport key from the registry (skips keyword resolution).
        observed_at: fixed timestamp for deterministic output (default: now UTC).
        max_targets: cap how many scrape targets to hit.

    Returns:
        List of raw-text EvidenceChunk (one per target that yielded text).
        Each target is isolated: one failed scrape never kills the bundle.
    """
    service = service or BrowserbaseService()
    observed_at = observed_at or _utc_now()
    cfg: SportConfig = get_sport_config(sport) if sport else resolve_sport(market)

    targets = list(cfg.scrape_targets)
    if max_targets is not None:
        targets = targets[:max_targets]

    chunks: List[EvidenceChunk] = []
    for target in targets:
        try:
            raw = service.scrape_text(target.url)
        except Exception:
            raw = None
        if raw:
            chunks.append(_make_noisy_chunk(raw, target, cfg, observed_at))
    return chunks
