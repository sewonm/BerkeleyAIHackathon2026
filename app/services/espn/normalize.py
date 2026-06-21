"""
Normalize ESPN JSON -> EvidenceChunk (SA-OUT-01).

Every normalizer:
- returns ``Optional[EvidenceChunk]`` (None when the source is absent), or a list,
- is individually defensive (the collector also wraps each call in try/except),
- stamps the four standard metadata keys + sport/source_strength/event identity,
- renders RAW readable text (the compression engine downstream cuts it down).

Metadata contract (rides in ``EvidenceChunk.metadata``):
    kind, fetched_via="http", sport, source_strength="anchor",
    observed_at, league, event_id, event_name
"""

from __future__ import annotations

from typing import Optional

from app.schemas.evidence import EvidenceChunk
from app.services.espn.registry import SportConfig

ANCHOR_STRENGTH = "anchor"  # ESPN HTTP = strong, deterministic source
FETCHED_VIA = "http"


# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def make_chunk(
    text: str,
    *,
    kind: str,
    cfg: SportConfig,
    observed_at: str,
    source_url: str,
    event_id: str,
    event_name: str,
    confidence: float = 0.9,
    extra: Optional[dict] = None,
) -> EvidenceChunk:
    metadata = {
        "kind": kind,
        "fetched_via": FETCHED_VIA,
        "sport": cfg.key,
        "source_strength": ANCHOR_STRENGTH,
        "observed_at": observed_at,
        "league": cfg.espn_league,
        "event_id": event_id,
        "event_name": event_name,
    }
    if extra:
        metadata.update(extra)
    return EvidenceChunk(
        source_type="sports_video",
        text=text.strip(),
        source_url=source_url,
        timestamp=observed_at,
        confidence=confidence,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _competitors(event: dict) -> tuple[dict, dict]:
    """Return (home, away) competitor dicts (empty dicts if missing)."""
    home: dict = {}
    away: dict = {}
    try:
        for c in event["competitions"][0]["competitors"]:
            if c.get("homeAway") == "home":
                home = c
            elif c.get("homeAway") == "away":
                away = c
    except (KeyError, IndexError, TypeError):
        pass
    return home, away


def _team_name(competitor: dict) -> str:
    t = competitor.get("team", {}) if competitor else {}
    return t.get("displayName") or t.get("name") or t.get("abbreviation") or "Unknown"


def _implied_prob_from_moneyline(american) -> Optional[float]:
    try:
        a = float(american)
    except (TypeError, ValueError):
        return None
    if a == 0:
        return None
    return round((-a) / ((-a) + 100), 4) if a < 0 else round(100 / (a + 100), 4)


# ---------------------------------------------------------------------------
# Normalizers  (one per evidence kind)
# ---------------------------------------------------------------------------

def normalize_score_state(
    event: dict, cfg: SportConfig, observed_at: str, source_url: str
) -> Optional[EvidenceChunk]:
    """SA-DATA-01 — live score + game state."""
    if not event:
        return None
    home, away = _competitors(event)
    event_id = str(event.get("id", ""))
    name = event.get("name") or f"{_team_name(away)} at {_team_name(home)}"
    try:
        status = event["status"]["type"]
        state = status.get("detail") or status.get("description") or status.get("state", "")
    except (KeyError, TypeError):
        state = ""
    hs = home.get("score", "?")
    as_ = away.get("score", "?")
    date = event.get("date", "")
    venue = ""
    try:
        venue = event["competitions"][0]["venue"]["fullName"]
    except (KeyError, IndexError, TypeError):
        pass

    text = (
        f"{cfg.display} — {name}\n"
        f"Score: {_team_name(away)} {as_} @ {_team_name(home)} {hs}\n"
        f"State: {state}"
        + (f"\nVenue: {venue}" if venue else "")
        + (f"\nDate: {date}" if date else "")
    )
    return make_chunk(
        text, kind="score_state", cfg=cfg, observed_at=observed_at,
        source_url=source_url, event_id=event_id, event_name=name, confidence=0.95,
    )


def normalize_box_stats(
    summary: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str,
) -> Optional[EvidenceChunk]:
    """SA-DATA-02 — team box/match statistics."""
    teams = (summary.get("boxscore") or {}).get("teams") or []
    if not teams:
        return None
    lines: list[str] = []
    for team in teams:
        tname = _team_name(team)
        rendered: list[str] = []
        for stat in team.get("statistics") or []:
            label = stat.get("label") or stat.get("name") or ""
            dv = stat.get("displayValue")
            if dv not in (None, ""):
                rendered.append(f"{label}: {dv}")
            for sub in stat.get("stats") or []:  # nested groups (e.g. MLB batting)
                slabel = sub.get("label") or sub.get("name") or ""
                sdv = sub.get("displayValue")
                if sdv not in (None, ""):
                    rendered.append(f"{slabel}: {sdv}")
        if rendered:
            lines.append(f"{tname} — " + "; ".join(rendered[:25]))
    if not lines:
        return None
    text = "Box/match statistics:\n" + "\n".join(lines)
    return make_chunk(
        text, kind="box_stats", cfg=cfg, observed_at=observed_at,
        source_url=source_url, event_id=event_id, event_name=event_name,
    )


def normalize_event_log(
    summary: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str, limit: int = 20,
) -> Optional[EvidenceChunk]:
    """SA-DATA-02 — event log (soccer keyEvents; else scoring plays)."""
    entries: list[str] = []

    key_events = summary.get("keyEvents") or []
    if key_events:
        for ke in key_events[:limit]:
            clock = (ke.get("clock") or {}).get("displayValue", "")
            txt = ke.get("text") or (ke.get("type") or {}).get("text") or ""
            team = (ke.get("team") or {}).get("displayName", "")
            who = ""
            parts = ke.get("participants") or []
            if parts:
                who = (parts[0].get("athlete") or {}).get("displayName", "")
            bits = [b for b in [clock, team, who, txt] if b]
            if bits:
                entries.append(" | ".join(bits))
    else:
        plays = summary.get("plays") or []
        scoring = [p for p in plays if p.get("scoringPlay")]
        for p in scoring[-limit:]:
            period = (p.get("period") or {}).get("displayValue", "")
            txt = p.get("text", "")
            if txt:
                entries.append(" | ".join(b for b in [period, txt] if b))

    if not entries:
        return None
    text = "Key game events:\n- " + "\n- ".join(entries)
    return make_chunk(
        text, kind="event_log", cfg=cfg, observed_at=observed_at,
        source_url=source_url, event_id=event_id, event_name=event_name,
    )


def normalize_odds(
    odds_json: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str,
) -> Optional[EvidenceChunk]:
    """SA-DATA-03 — odds incl. open/close/current line movement (core API)."""
    items = (odds_json or {}).get("items") or []
    if not items:
        return None
    it = items[0]
    provider = (it.get("provider") or {}).get("name", "Unknown book")

    def _ml(side: str) -> str:
        cur = (it.get(side) or {}).get("current") or {}
        ml = (cur.get("moneyLine") or {}).get("american")
        if ml is None:
            ml = (it.get(side) or {}).get("moneyLine")
        return str(ml) if ml is not None else "n/a"

    def _readable(block: dict) -> Optional[str]:
        # ESPN movement sub-objects expose the human line as alternateDisplayValue
        # (e.g. "8.5"), then american, then displayValue.
        if not isinstance(block, dict):
            return str(block) if block not in (None, "") else None
        for key in ("alternateDisplayValue", "american", "displayValue", "value"):
            v = block.get(key)
            if v not in (None, "", 0.0):
                return str(v)
        return None

    def _line(block_key: str) -> str:
        b = it.get(block_key) or {}
        bits = []
        total = _readable(b.get("total") or b.get("overUnder"))
        if total:
            bits.append(f"O/U {total}")
        spread = _readable(b.get("spread") or b.get("pointSpread"))
        if spread:
            bits.append(f"spread {spread}")
        return ", ".join(bits) if bits else "n/a"

    lines = [
        f"Odds ({provider}) for {event_name}:",
        f"Details: {it.get('details', 'n/a')}",
        f"Current spread: {it.get('spread', 'n/a')} | over/under: {it.get('overUnder', 'n/a')}",
        f"Line movement — open: {_line('open')} | close: {_line('close')} | current: {_line('current')}",
        f"Moneyline (current) — home: {_ml('homeTeamOdds')} | away: {_ml('awayTeamOdds')}",
    ]
    text = "\n".join(lines)
    return make_chunk(
        text, kind="odds", cfg=cfg, observed_at=observed_at, source_url=source_url,
        event_id=event_id, event_name=event_name, confidence=0.9,
    )


def normalize_win_probability(
    summary: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str,
) -> Optional[EvidenceChunk]:
    """SA-DATA-04 — win prob (ESPN model if present) + implied prob from moneyline."""
    parts: list[str] = []

    # ESPN model win-probability series (last entry = latest)
    wp = summary.get("winprobability") or []
    if wp:
        last = wp[-1]
        hp = last.get("homeWinPercentage")
        tie = last.get("tiePercentage", 0) or 0
        if hp is not None:
            home_pct = round(float(hp) * 100, 1)
            away_pct = round((1 - float(hp) - float(tie)) * 100, 1)
            parts.append(
                f"ESPN model win probability — home {home_pct}% | away {away_pct}%"
                + (f" | draw {round(float(tie) * 100, 1)}%" if tie else "")
            )

    # Implied probability from current moneyline (works across sports)
    pc = summary.get("pickcenter") or []
    if pc:
        ho = pc[0].get("homeTeamOdds") or {}
        ao = pc[0].get("awayTeamOdds") or {}
        hi = _implied_prob_from_moneyline(ho.get("moneyLine"))
        ai = _implied_prob_from_moneyline(ao.get("moneyLine"))
        if hi is not None or ai is not None:
            parts.append(
                "Implied probability (moneyline) — "
                f"home {round((hi or 0) * 100, 1)}% | away {round((ai or 0) * 100, 1)}%"
            )

    if not parts:
        return None
    text = "Win / implied probability:\n" + "\n".join(parts)
    return make_chunk(
        text, kind="win_probability", cfg=cfg, observed_at=observed_at,
        source_url=source_url, event_id=event_id, event_name=event_name, confidence=0.9,
    )


def normalize_injuries(
    summary: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str, per_team: int = 12,
) -> Optional[EvidenceChunk]:
    """SA-DATA-05 — injuries / availability."""
    injuries = summary.get("injuries") or []
    blocks: list[str] = []
    for team_block in injuries:
        tname = _team_name(team_block)
        items = team_block.get("injuries") or []
        rendered = []
        for inj in items[:per_team]:
            ath = (inj.get("athlete") or {}).get("displayName", "Unknown")
            status = inj.get("status") or (inj.get("type") or {}).get("description", "")
            rendered.append(f"{ath} ({status})" if status else ath)
        if rendered:
            blocks.append(f"{tname}: " + "; ".join(rendered))
    if not blocks:
        return None
    text = "Injuries / availability:\n" + "\n".join(blocks)
    return make_chunk(
        text, kind="injuries", cfg=cfg, observed_at=observed_at, source_url=source_url,
        event_id=event_id, event_name=event_name, confidence=0.85,
    )


def normalize_lineups(
    summary: dict, cfg: SportConfig, observed_at: str, source_url: str,
    event_id: str, event_name: str, per_team: int = 11,
) -> Optional[EvidenceChunk]:
    """SA-DATA-05 — lineups / rosters (starters)."""
    rosters = summary.get("rosters") or []
    blocks: list[str] = []
    for team_block in rosters:
        tname = _team_name(team_block)
        entries = team_block.get("roster") or []
        starters = [e for e in entries if e.get("starter")]
        chosen = starters or entries
        names = []
        for e in chosen[:per_team]:
            ath = (e.get("athlete") or {}).get("displayName", "")
            pos = (e.get("position") or {})
            pos_abbr = pos.get("abbreviation") if isinstance(pos, dict) else ""
            if ath:
                names.append(f"{ath} ({pos_abbr})" if pos_abbr else ath)
        if names:
            label = "starters" if starters else "roster"
            blocks.append(f"{tname} {label}: " + ", ".join(names))
    if not blocks:
        return None
    text = "Lineups / rosters:\n" + "\n".join(blocks)
    return make_chunk(
        text, kind="lineups", cfg=cfg, observed_at=observed_at, source_url=source_url,
        event_id=event_id, event_name=event_name, confidence=0.85,
    )
