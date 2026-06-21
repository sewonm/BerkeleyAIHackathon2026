"""
Phase 5 — deployed uAgent bundle-logic tests (offline, no uAgent constructed).

Imports uagents_deploy/sports_evidence.py directly (not the agent) so we can test
the exact bundle the deployed agent will send over Chat / EvidenceResponse, without
network or a running agent.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = REPO_ROOT / "uagents_deploy"
ESPN_FIX = REPO_ROOT / "tests" / "fixtures" / "espn"

# Make `import sports_evidence` (and its `from protocols.messages import ...`) resolve.
if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))

import sports_evidence as SE  # noqa: E402


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    """Force the bundle to come from recorded fixtures (deterministic, no network)."""
    monkeypatch.setenv("ESPN_FIXTURES_DIR", str(ESPN_FIX))
    monkeypatch.setenv("ESPN_OFFLINE", "1")
    monkeypatch.setenv("BROWSERBASE_OFFLINE", "1")


def _extract_bundle_json(text: str):
    """Mirror of send_test_chat.py's parser — proves the reply is machine-readable."""
    if "```json" in text:
        body = text.split("```json", 1)[1].split("```", 1)[0].strip()
        return json.loads(body)
    return json.loads(text)


def test_live_layer_importable():
    assert SE.LIVE_AVAILABLE, f"app package not importable: {SE.IMPORT_ERR}"


def test_collect_bundle_merges_anchor_and_noisy():
    msgs, meta = SE.collect_bundle("Will Argentina win the World Cup soccer match?")
    assert len(msgs) >= 2
    assert all(m.source_type == "sports_video" for m in msgs)
    vias = {m.metadata.get("fetched_via") for m in msgs}
    assert "http" in vias        # ESPN anchor
    assert "browserbase" in vias  # noisy
    assert meta["sport"] == "soccer"
    assert meta["source"] in {"live", "fixtures"}


def test_collect_bundle_query_aware_baseball():
    msgs, meta = SE.collect_bundle("Will the Yankees win this MLB baseball game?")
    assert meta["sport"] == "baseball"
    assert len(msgs) >= 2


def test_chat_reply_is_readable_and_machine_parseable():
    question = "Will Argentina win the World Cup soccer match?"
    msgs, meta = SE.collect_bundle(question)
    reply = SE.format_chat_reply(question, msgs, meta)

    # human-readable header
    assert "Sports evidence bundle" in reply
    assert "soccer" in reply
    # machine-readable: the fenced JSON block round-trips to the same chunks
    parsed = _extract_bundle_json(reply)
    assert len(parsed) == len(msgs)
    assert all(c["source_type"] == "sports_video" for c in parsed)


def test_stub_bundle_is_valid_fallback():
    stub = SE.build_stub_bundle("anything")
    assert len(stub) >= 2
    for m in stub:
        assert m.source_type == "sports_video"
        assert {"kind", "fetched_via", "source_strength", "observed_at"} <= set(m.metadata)
        assert m.metadata["fetched_via"] == "stub"


def test_to_msg_roundtrips_evidence_chunk():
    from app.schemas.evidence import EvidenceChunk
    c = EvidenceChunk(
        source_type="sports_video", text="hello", source_url="http://x",
        timestamp="2026-06-20T00:00:00Z", confidence=0.9,
        metadata={"kind": "score_state", "fetched_via": "http"},
    )
    m = SE.to_msg(c)
    assert m.source_type == "sports_video"
    assert m.text == "hello"
    assert m.metadata["kind"] == "score_state"
