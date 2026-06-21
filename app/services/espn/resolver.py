"""
Event resolution (SA-DATA-01, resolution half).

Given a sport config + (optional) market, pick the relevant game event from the
ESPN scoreboard with NO hardcoded sport: prefer a team mentioned in the market,
then a live game, then the most-recent finished game, then the next scheduled.
"""

from __future__ import annotations

from typing import Optional

from app.services.espn.client import ESPNClient
from app.services.espn.fetchers import fetch_scoreboard
from app.services.espn.registry import SportConfig


def _state(event: dict) -> str:
    try:
        return event["status"]["type"]["state"]  # "pre" | "in" | "post"
    except (KeyError, TypeError):
        return ""


def _competitor_terms(event: dict) -> list[str]:
    terms: list[str] = []
    try:
        for c in event["competitions"][0]["competitors"]:
            team = c.get("team", {})
            for k in ("displayName", "shortDisplayName", "name", "location", "abbreviation"):
                v = team.get(k)
                if v:
                    terms.append(str(v).lower())
    except (KeyError, IndexError, TypeError):
        pass
    return terms


def _market_text(market) -> str:
    if market is None:
        return ""
    if isinstance(market, str):
        return market.lower()
    parts = [
        getattr(market, "question", "") or "",
        getattr(market, "title", "") or "",
    ]
    return " ".join(parts).lower()


def resolve_event(
    client: ESPNClient, cfg: SportConfig, market=None
) -> Optional[dict]:
    """Resolve the target event.

    Returns:
        ``{"event": <raw scoreboard event>, "event_id": str, "competition_id": str}``
        or None if the scoreboard is empty/unavailable.
    """
    sb = fetch_scoreboard(client, cfg)
    if not sb:
        return None
    events = sb.get("events") or []
    if not events:
        return None

    chosen: Optional[dict] = None

    # 1) market team mention (entity-light; full targeting is Phase 4)
    text = _market_text(market)
    if text:
        for ev in events:
            if any(term and term in text for term in _competitor_terms(ev)):
                chosen = ev
                break

    # 2) live -> 3) most-recent finished -> 4) next scheduled -> 5) first
    if chosen is None:
        live = [e for e in events if _state(e) == "in"]
        if live:
            chosen = live[0]
        else:
            post = sorted(
                (e for e in events if _state(e) == "post"),
                key=lambda e: e.get("date", ""),
                reverse=True,
            )
            if post:
                chosen = post[0]
            else:
                pre = sorted(
                    (e for e in events if _state(e) == "pre"),
                    key=lambda e: e.get("date", ""),
                )
                chosen = pre[0] if pre else events[0]

    try:
        comp = (chosen.get("competitions") or [{}])[0]
        comp_id = comp.get("id") or chosen.get("id")
    except (AttributeError, TypeError):
        comp_id = chosen.get("id")

    return {
        "event": chosen,
        "event_id": str(chosen.get("id")),
        "competition_id": str(comp_id),
    }
