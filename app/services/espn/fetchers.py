"""
ESPN endpoint fetchers + URL builders (sport-agnostic).

URL families (note the asymmetry — this trips people up):
- Site API : site.api.espn.com/apis/site/v2/sports/{sport}/{league}/...        (NO 'leagues')
- Core API : sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/...   (WITH 'leagues')

Every fetcher returns the raw decoded JSON (or None). They never raise — the
client already swallows network errors and returns None.
"""

from __future__ import annotations

from typing import Optional

from app.services.espn.client import ESPNClient
from app.services.espn.registry import SportConfig

SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports"
CORE_BASE = "https://sports.core.api.espn.com/v2/sports"


# -- URL builders ----------------------------------------------------------

def scoreboard_url(cfg: SportConfig) -> str:
    return f"{SITE_BASE}/{cfg.espn_sport}/{cfg.espn_league}/scoreboard"


def summary_url(cfg: SportConfig) -> str:
    return f"{SITE_BASE}/{cfg.espn_sport}/{cfg.espn_league}/summary"


def odds_url(cfg: SportConfig, event_id: str, competition_id: str) -> str:
    return (
        f"{CORE_BASE}/{cfg.espn_sport}/leagues/{cfg.espn_league}"
        f"/events/{event_id}/competitions/{competition_id}/odds"
    )


def probabilities_url(cfg: SportConfig, event_id: str, competition_id: str) -> str:
    return (
        f"{CORE_BASE}/{cfg.espn_sport}/leagues/{cfg.espn_league}"
        f"/events/{event_id}/competitions/{competition_id}/probabilities"
    )


# -- fetchers --------------------------------------------------------------

def fetch_scoreboard(client: ESPNClient, cfg: SportConfig) -> Optional[dict]:
    """Scoreboard listing — used to resolve the live/most-recent event."""
    return client.get_json(scoreboard_url(cfg))


def fetch_summary(client: ESPNClient, cfg: SportConfig, event_id: str) -> Optional[dict]:
    """Per-game summary: boxscore, plays/keyEvents, injuries, rosters, odds, win-prob."""
    return client.get_json(summary_url(cfg), {"event": event_id})


def fetch_odds(
    client: ESPNClient, cfg: SportConfig, event_id: str, competition_id: str
) -> Optional[dict]:
    """Core-API odds with open/close/current line movement."""
    return client.get_json(odds_url(cfg, event_id, competition_id))


def fetch_probabilities(
    client: ESPNClient, cfg: SportConfig, event_id: str, competition_id: str
) -> Optional[dict]:
    """Core-API win-probability series (not modeled for every sport)."""
    return client.get_json(
        probabilities_url(cfg, event_id, competition_id), {"limit": 200}
    )
