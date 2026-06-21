"""
Redis Agent Memory Service — persistent two-tier memory for SignalForge agents.

Session memory  : per-market evidence collected by agents in a single run
Long-term memory: final decisions stored across runs (system learns over time)

ENV VARS:
  AGENT_MEMORY_URL      (default: https://gcp-us-east4.memory.redis.io)
  AGENT_MEMORY_STORE_ID
  AGENT_MEMORY_API_KEY
"""

import os
import time

_MEMORY_URL = os.getenv("AGENT_MEMORY_URL", "https://gcp-us-east4.memory.redis.io")
_STORE_ID = os.getenv("AGENT_MEMORY_STORE_ID", "")
_API_KEY = os.getenv("AGENT_MEMORY_API_KEY", "")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _STORE_ID or not _API_KEY:
        raise RuntimeError("AGENT_MEMORY_STORE_ID and AGENT_MEMORY_API_KEY must be set")
    from redis_agent_memory import AgentMemory
    _client = AgentMemory(_MEMORY_URL, store_id=_STORE_ID, api_key=_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Session memory — evidence from agents within one market analysis run
# ---------------------------------------------------------------------------

def store_evidence(market_id: str, agent_name: str, text: str) -> bool:
    """Store an agent's evidence finding as a session event."""
    try:
        from redis_agent_memory import models
        _get_client().add_session_event(
            session_id=market_id,
            actor_id=agent_name,
            role=models.MessageRole.USER,
            content=[{"text": text}],
            created_at=int(time.time() * 1000),
        )
        return True
    except Exception:
        return False


def get_session_evidence(market_id: str):
    """Retrieve all evidence collected for a market in this run."""
    try:
        return _get_client().get_session_memory(session_id=market_id)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Long-term memory — final decisions persist across runs
# ---------------------------------------------------------------------------

def store_decision(market_id: str, decision: str, confidence: float, reasoning: str) -> bool:
    """Store a final market decision in long-term memory."""
    try:
        text = (
            f"Market: {market_id} | Decision: {decision} | "
            f"Confidence: {confidence:.0%} | Reasoning: {reasoning}"
        )
        _get_client().bulk_create_long_term_memories(memories=[
            {"id": f"decision-{market_id}-{int(time.time())}", "text": text}
        ])
        return True
    except Exception:
        return False


def search_past_decisions(query: str, limit: int = 3):
    """Semantic search over past market decisions."""
    try:
        return _get_client().search_long_term_memory(
            request={"text": query, "limit": limit}
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def ping() -> bool:
    try:
        _get_client()
        return True
    except Exception:
        return False
