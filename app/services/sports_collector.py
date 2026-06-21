"""
Merged, query-aware sports evidence collector (Phase 4).

This is the sports agent's CLEAN OUTPUT CONTRACT (SA-OUT-03): one call that
resolves the sport from the market, pulls the ESPN HTTP anchor (Phase 2) and the
Browserbase noisy layer (Phase 3), and returns a single merged, de-duplicated
``list[EvidenceChunk]`` — ready for the downstream compression engine (wiring
deferred).

Query-aware (SA-OUT-02): the market question drives
- which sport/league + game event is resolved (entity/team mention -> live game),
- which noisy sources are targeted (from the sport's registry),
so different markets yield different targeted bundles.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.evidence import EvidenceChunk
from app.services.espn.client import ESPNClient
from app.services.espn.collector import collect_espn_evidence
from app.services.espn.registry import SportConfig, get_sport_config, resolve_sport
from app.services.browserbase_service import BrowserbaseService
from app.services.noisy_collector import collect_noisy_evidence


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Query-awareness (SA-OUT-02)
# ---------------------------------------------------------------------------

# Stopwords so "Will The Yankees" doesn't surface "Will"/"The" as entities.
_STOP = {
    "Will", "The", "Is", "Are", "Do", "Does", "Did", "Who", "What", "When",
    "Over", "Under", "Yes", "No", "A", "An", "In", "On", "At", "To", "Of",
}


def derive_entities(market) -> dict:
    """Derive query entities (teams/players, numeric thresholds) from a market.

    Lightweight + dependency-free: proper-noun phrases drive source targeting and
    are recorded on the bundle so the collection is demonstrably query-aware.
    """
    if isinstance(market, str):
        text = market
        protected = []
    else:
        text = f"{getattr(market, 'question', '') or ''} {getattr(market, 'title', '') or ''}"
        protected = list(getattr(market, "protected_terms", []) or [])

    proper = re.findall(r"\b[A-Z][a-zA-Z'.]+(?:\s+[A-Z][a-zA-Z'.]+)*\b", text)
    entities = []
    for phrase in proper:
        # drop leading stopwords like "Will"/"The" from a phrase
        words = [w for w in phrase.split() if w not in _STOP]
        cleaned = " ".join(words).strip()
        if len(cleaned) >= 3 and cleaned not in entities:
            entities.append(cleaned)

    thresholds = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    # merge protected terms (already curated entities) to the front
    for pt in protected:
        if pt and pt not in entities:
            entities.insert(0, pt)
    return {"entities": entities, "thresholds": thresholds, "protected_terms": protected}


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def _dedupe(chunks: List[EvidenceChunk]) -> List[EvidenceChunk]:
    seen = set()
    out: List[EvidenceChunk] = []
    for c in chunks:
        key = (c.metadata.get("kind"), c.source_url, (c.text or "")[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def collect_sports_evidence(
    market,
    *,
    sport: Optional[str] = None,
    observed_at: Optional[str] = None,
    anchor: bool = True,
    noisy: bool = True,
    espn_client: Optional[ESPNClient] = None,
    browserbase: Optional[BrowserbaseService] = None,
    max_noisy: Optional[int] = None,
) -> List[EvidenceChunk]:
    """Collect the merged sports evidence bundle for a market.

    Args:
        market: Market (or string). Drives sport + event resolution.
        sport: force a registry sport key (skips keyword resolution).
        observed_at: fixed timestamp for deterministic output (default: now UTC).
        anchor: include the ESPN HTTP anchor layer (Phase 2).
        noisy: include the Browserbase noisy layer (Phase 3).
        espn_client / browserbase: inject configured services (fixtures/cache/live).
        max_noisy: cap noisy scrape targets.

    Returns:
        Merged, de-duplicated ``list[EvidenceChunk]`` (anchor first, then noisy).
        Each layer is isolated — a failure in one never kills the other.
    """
    observed_at = observed_at or _utc_now()
    cfg: SportConfig = get_sport_config(sport) if sport else resolve_sport(market)

    chunks: List[EvidenceChunk] = []

    if anchor:
        try:
            chunks.extend(
                collect_espn_evidence(
                    market, client=espn_client, sport=cfg.key, observed_at=observed_at
                )
            )
        except Exception:
            pass

    if noisy:
        try:
            chunks.extend(
                collect_noisy_evidence(
                    market, service=browserbase, sport=cfg.key,
                    observed_at=observed_at, max_targets=max_noisy,
                )
            )
        except Exception:
            pass

    return _dedupe(chunks)
