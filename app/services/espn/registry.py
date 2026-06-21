"""
Sport -> source registry (SA-DATA-06).

This is the ONE place that knows about sports. Adding a sport = adding a
``SportConfig`` entry here; the ESPN client, resolver, fetchers, normalizer and
collector are all sport-agnostic and read from this registry. No pipeline code
changes when a sport is added.

Each entry carries:
- ESPN ``{sport}/{league}`` slugs (the uniform ESPN URL pattern).
- ``keywords`` used to resolve a Kalshi market -> sport with no hardcoding.
- ``scrape_targets`` consumed by the Phase 3 Browserbase noisy layer (kept here
  so the "config-only" promise covers the noisy layer too).

Validated live (2026-06-20): soccer/fifa.world (FIFA World Cup) + baseball/mlb.
nba / nfl are included to prove generality (config-only, no fixtures required).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ScrapeTarget:
    """A Phase 3 noisy-layer scrape target (raw text only)."""

    kind: str          # evidence kind, e.g. "deep_stats", "match_thread", "beat_news"
    label: str         # human/source label, e.g. "FBref", "Reddit r/worldcup"
    url: str           # URL to scrape raw readable text from
    source_strength: str = "noisy"


@dataclass(frozen=True)
class SportConfig:
    """Everything the pipeline needs to handle one sport, config-only."""

    key: str                       # canonical sport key, e.g. "soccer"
    display: str                   # human label, e.g. "Soccer (FIFA World Cup)"
    espn_sport: str                # ESPN sport slug, e.g. "soccer"
    espn_league: str               # ESPN league slug, e.g. "fifa.world"
    keywords: tuple[str, ...]      # market-text keywords that select this sport
    scrape_targets: tuple[ScrapeTarget, ...] = field(default_factory=tuple)

    @property
    def slug(self) -> str:
        """ESPN ``{sport}/{league}`` slug, e.g. ``soccer/fifa.world``."""
        return f"{self.espn_sport}/{self.espn_league}"


# ---------------------------------------------------------------------------
# The registry. Add a sport here and the whole pipeline supports it.
# ---------------------------------------------------------------------------

SPORT_REGISTRY: dict[str, SportConfig] = {
    "soccer": SportConfig(
        key="soccer",
        display="Soccer (FIFA World Cup)",
        espn_sport="soccer",
        espn_league="fifa.world",
        keywords=(
            "world cup", "fifa", "soccer", "football match", "uefa", "premier league",
            "la liga", "champions league", "messi", "argentina", "brazil", "group stage",
        ),
        scrape_targets=(
            ScrapeTarget(
                kind="deep_stats",
                label="FBref World Cup",
                url="https://fbref.com/en/comps/1/World-Cup-Stats",
            ),
            ScrapeTarget(
                kind="match_thread",
                label="Reddit r/worldcup",
                url="https://www.reddit.com/r/worldcup/hot/.json?limit=10",
            ),
            ScrapeTarget(
                kind="live_stats",
                label="Sofascore World Cup",
                url="https://www.sofascore.com/tournament/football/world/world-cup/16",
            ),
        ),
    ),
    "baseball": SportConfig(
        key="baseball",
        display="Baseball (MLB)",
        espn_sport="baseball",
        espn_league="mlb",
        keywords=(
            "mlb", "baseball", "world series", "yankees", "dodgers", "home run",
            "pitcher", "innings", "al east", "nl west",
        ),
        scrape_targets=(
            ScrapeTarget(
                kind="deep_stats",
                label="Baseball Reference",
                url="https://www.baseball-reference.com/leagues/majors/2026-standings.shtml",
            ),
            ScrapeTarget(
                kind="match_thread",
                label="Reddit r/baseball",
                url="https://www.reddit.com/r/baseball/hot/.json?limit=10",
            ),
        ),
    ),
    # --- generality proof: config-only, no fixtures shipped for these ---
    "basketball": SportConfig(
        key="basketball",
        display="Basketball (NBA)",
        espn_sport="basketball",
        espn_league="nba",
        keywords=("nba", "basketball", "finals", "lakers", "celtics", "playoffs"),
        scrape_targets=(
            ScrapeTarget(
                kind="match_thread",
                label="Reddit r/nba",
                url="https://www.reddit.com/r/nba/hot/.json?limit=10",
            ),
        ),
    ),
    "football": SportConfig(
        key="football",
        display="American Football (NFL)",
        espn_sport="football",
        espn_league="nfl",
        keywords=("nfl", "super bowl", "touchdown", "quarterback", "afc", "nfc"),
        scrape_targets=(
            ScrapeTarget(
                kind="match_thread",
                label="Reddit r/nfl",
                url="https://www.reddit.com/r/nfl/hot/.json?limit=10",
            ),
        ),
    ),
}

DEFAULT_SPORT_KEY = "soccer"  # demo showcase: 2026 FIFA World Cup


def get_sport_config(sport_key: str) -> SportConfig:
    """Return the ``SportConfig`` for ``sport_key`` (KeyError if unknown)."""
    return SPORT_REGISTRY[sport_key]


def resolve_sport(market, default: Optional[str] = None) -> SportConfig:
    """Resolve a market to a ``SportConfig`` from registry keywords (no hardcoding).

    Scans the market's question + title + category for each sport's keywords and
    returns the best match. Falls back to ``default`` (or ``DEFAULT_SPORT_KEY``).

    Args:
        market: object with ``.question`` / ``.title`` / ``.category`` (or a str).
        default: sport key to use when nothing matches.

    Returns:
        The matched ``SportConfig``.
    """
    if isinstance(market, str):
        haystack = market.lower()
    else:
        parts = [
            getattr(market, "question", "") or "",
            getattr(market, "title", "") or "",
            getattr(market, "category", "") or "",
        ]
        haystack = " ".join(parts).lower()

    best_key: Optional[str] = None
    best_score = 0
    for key, cfg in SPORT_REGISTRY.items():
        score = sum(1 for kw in cfg.keywords if kw in haystack)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is None:
        best_key = default or DEFAULT_SPORT_KEY
    return SPORT_REGISTRY[best_key]
