"""
Evidence-bundle logic for the deployed sports uAgent (Phase 5).

Kept separate from sports_video_agent.py so the bundle building is importable and
unit-testable WITHOUT constructing a uAgent / touching the network. The deployed
agent imports collect_bundle / format_chat_reply / build_stub_bundle from here.

Mailbox agent runs locally, so this imports the project collectors (app.services.*)
to return REAL evidence; it degrades to recorded fixtures, then a stub bundle, so a
reply is NEVER empty.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone

from protocols.messages import EvidenceChunkMsg

# --- locate the repo so we can import the app package + reach the fixtures ---
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

ESPN_FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures", "espn")
NOISY_FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures", "noisy")
ESPN_CACHE = os.path.join(REPO_ROOT, ".cache", "espn")

try:
    from app.schemas.market import Market
    from app.services.sports_collector import collect_sports_evidence, derive_entities
    from app.services.espn.client import ESPNClient
    from app.services.browserbase_service import BrowserbaseService

    LIVE_AVAILABLE = True
    IMPORT_ERR = None
except Exception as exc:  # pragma: no cover - defensive
    LIVE_AVAILABLE = False
    IMPORT_ERR = exc


def to_msg(chunk) -> EvidenceChunkMsg:
    """Convert an app EvidenceChunk into the transport EvidenceChunkMsg."""
    return EvidenceChunkMsg(
        source_type=chunk.source_type,
        text=chunk.text,
        source_url=chunk.source_url,
        timestamp=chunk.timestamp,
        confidence=chunk.confidence,
        metadata=dict(chunk.metadata or {}),
    )


def build_stub_bundle(market_question: str) -> list:
    """Tiny canned bundle — last-resort fallback so a reply is never empty."""
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = (market_question or "")[:60]
    return [
        EvidenceChunkMsg(
            source_type="sports_video",
            text=f"(stub) Argentina 2-1 Brazil — re: {preview}",
            source_url="stub://sports/fallback",
            confidence=0.5,
            metadata={"kind": "scoreline", "fetched_via": "stub",
                      "source_strength": "stub", "observed_at": observed_at},
        ),
        EvidenceChunkMsg(
            source_type="sports_video",
            text="(stub) Star striker listed as questionable with an ankle knock.",
            source_url="stub://sports/fallback",
            confidence=0.5,
            metadata={"kind": "injury", "fetched_via": "stub",
                      "source_strength": "stub", "observed_at": observed_at},
        ),
    ]


def collect_bundle(question: str, category: str = "sports"):
    """Build the evidence bundle for a market question. BLOCKING (run in a thread).

    Returns ``(list[EvidenceChunkMsg], meta)``. Demo-safe ladder:
    live (ESPN net + cache, noisy fixtures) -> recorded fixtures -> stub.
    Never raises.
    """
    if not LIVE_AVAILABLE:
        return build_stub_bundle(question), {"source": "stub", "sport": None, "event": None, "entities": []}

    market = Market(
        market_id="chat-query",
        title=question or "sports market",
        question=question or "sports market",
        category=category or "sports",
        resolution_criteria="Resolves per the official sport result.",
    )

    chunks = []
    source = "live"
    try:
        chunks = collect_sports_evidence(
            market,
            espn_client=ESPNClient(cache_dir=ESPN_CACHE),
            browserbase=BrowserbaseService(fixtures_dir=NOISY_FIXTURES),
        )
    except Exception:
        chunks = []

    if len(chunks) < 2:  # network down / no live game -> recorded fixtures
        source = "fixtures"
        try:
            chunks = collect_sports_evidence(
                market,
                espn_client=ESPNClient(fixtures_dir=ESPN_FIXTURES, offline=True),
                browserbase=BrowserbaseService(fixtures_dir=NOISY_FIXTURES, offline=True),
            )
        except Exception:
            chunks = []

    if len(chunks) < 2:
        return build_stub_bundle(question), {"source": "stub", "sport": None, "event": None, "entities": []}

    meta = {
        "source": source,
        "sport": chunks[0].metadata.get("sport"),
        "event": chunks[0].metadata.get("event_name"),
        "entities": derive_entities(market).get("entities", [])[:6],
    }
    return [to_msg(c) for c in chunks], meta


def format_chat_reply(question: str, msgs: list, meta: dict) -> str:
    """Human-readable evidence summary for ASI:One + full JSON bundle for machines."""
    anchor = [m for m in msgs if m.metadata.get("fetched_via") == "http"]
    noisy = [m for m in msgs if m.metadata.get("fetched_via") == "browserbase"]

    lines = [f'🏟️ Sports evidence bundle for: "{(question or "").strip()[:140]}"']
    if meta.get("sport"):
        head = f"Sport: {meta['sport']}"
        if meta.get("event"):
            head += f" — {meta['event']}"
        lines.append(head)
    if meta.get("entities"):
        lines.append("Entities: " + ", ".join(meta["entities"]))
    lines.append(
        f"Source: {meta.get('source', 'live')} • {len(msgs)} chunks "
        f"({len(anchor)} live-stats anchor / {len(noisy)} noisy scrape)"
    )
    lines.append("")
    for m in msgs:
        first = (m.text or "").splitlines()[0] if m.text else ""
        lines.append(f"• [{m.metadata.get('kind', '?')}] {first[:100]}")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps([m.model_dump() for m in msgs], default=str))
    lines.append("```")
    return "\n".join(lines)
