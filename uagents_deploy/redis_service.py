"""
Redis service — shared data contract for all agents.

INSTALL:
  pip install redis

ENV VARS:
  REDIS_URL   (default: redis://localhost:6379)

KEY SCHEMA (everyone reads/writes these — do not invent new key names):

  market:{market_id}:snapshot       → current Kalshi price + volume
  market:{market_id}:claims         → raw evidence claims list from all agents
  market:{market_id}:compressed     → compressed evidence packet (post-compression)
  market:{market_id}:decision       → final YES/NO/HOLD output
  game:{game_id}:state              → live game score + clock
  game:{game_id}:stats:{entity_id}  → player or team stats
  stream:game:{game_id}:events      → Redis Stream of live events
  user:{user_id}:portfolio          → paper trading positions + cash
  leaderboard:paper_trading         → Redis sorted set, score = PnL

WHO WRITES WHAT:
  market_agent        → :snapshot
  web/video/stats     → :claims  (append, not overwrite)
  compression agent   → :compressed
  decision agent      → :decision
  game data feed      → :state, :stats:*, stream:events
  frontend/demo       → :portfolio, leaderboard
"""

import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_client = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


# ---------------------------------------------------------------------------
# Market snapshot
# ---------------------------------------------------------------------------

def set_market_snapshot(market_id: str, snapshot: dict):
    """market_agent writes this after fetching Kalshi price."""
    key = f"market:{market_id}:snapshot"
    get_client().set(key, json.dumps(snapshot))


def get_market_snapshot(market_id: str) -> dict | None:
    raw = get_client().get(f"market:{market_id}:snapshot")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Evidence claims  (web + video + stats agents all append here)
# ---------------------------------------------------------------------------

def append_claims(market_id: str, new_claims: list[dict]):
    """
    Each research agent appends its claims to the shared list.
    Do NOT overwrite — use append so all agents contribute.
    """
    key = f"market:{market_id}:claims"
    existing_raw = get_client().get(key)
    existing = json.loads(existing_raw) if existing_raw else []
    existing.extend(new_claims)
    get_client().set(key, json.dumps(existing))


def get_claims(market_id: str) -> list[dict]:
    raw = get_client().get(f"market:{market_id}:claims")
    return json.loads(raw) if raw else []


def clear_claims(market_id: str):
    """Call before a fresh analysis run."""
    get_client().delete(f"market:{market_id}:claims")


# ---------------------------------------------------------------------------
# Compressed evidence packet  (compression agent writes this)
# ---------------------------------------------------------------------------

def set_compressed(market_id: str, packet: dict):
    key = f"market:{market_id}:compressed"
    get_client().set(key, json.dumps(packet))


def get_compressed(market_id: str) -> dict | None:
    raw = get_client().get(f"market:{market_id}:compressed")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Decision output  (decision agent writes this)
# ---------------------------------------------------------------------------

def set_decision(market_id: str, decision: dict):
    key = f"market:{market_id}:decision"
    get_client().set(key, json.dumps(decision))


def get_decision(market_id: str) -> dict | None:
    raw = get_client().get(f"market:{market_id}:decision")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Live game state
# ---------------------------------------------------------------------------

def set_game_state(game_id: str, state: dict):
    get_client().set(f"game:{game_id}:state", json.dumps(state))


def get_game_state(game_id: str) -> dict | None:
    raw = get_client().get(f"game:{game_id}:state")
    return json.loads(raw) if raw else None


def set_entity_stats(game_id: str, entity_id: str, stats: dict):
    get_client().set(f"game:{game_id}:stats:{entity_id}", json.dumps(stats))


def get_entity_stats(game_id: str, entity_id: str) -> dict | None:
    raw = get_client().get(f"game:{game_id}:stats:{entity_id}")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Event stream  (Redis Streams — live play-by-play)
# ---------------------------------------------------------------------------

def push_event(game_id: str, event: dict):
    """Append a live event to the game stream."""
    get_client().xadd(f"stream:game:{game_id}:events", event)


def get_recent_events(game_id: str, count: int = 20) -> list[dict]:
    """Read the last N events from the game stream."""
    entries = get_client().xrevrange(f"stream:game:{game_id}:events", count=count)
    return [fields for _, fields in entries]


# ---------------------------------------------------------------------------
# Paper trading portfolio
# ---------------------------------------------------------------------------

def set_portfolio(user_id: str, portfolio: dict):
    get_client().set(f"user:{user_id}:portfolio", json.dumps(portfolio))


def get_portfolio(user_id: str) -> dict | None:
    raw = get_client().get(f"user:{user_id}:portfolio")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Leaderboard  (Redis sorted set — score = paper PnL)
# ---------------------------------------------------------------------------

def update_leaderboard(user_id: str, pnl: float):
    get_client().zadd("leaderboard:paper_trading", {user_id: pnl})


def get_leaderboard(top_n: int = 10) -> list[tuple[str, float]]:
    """Returns [(user_id, pnl), ...] sorted highest first."""
    return get_client().zrevrange("leaderboard:paper_trading", 0, top_n - 1, withscores=True)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def ping() -> bool:
    try:
        return get_client().ping()
    except Exception:
        return False
