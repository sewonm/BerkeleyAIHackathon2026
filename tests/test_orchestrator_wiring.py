"""
Phase 3, Plan 01 — Orchestrator wiring tests (offline, keyless, no uAgent constructed).

Discipline: ALL tests run offline with no network, no real key, no live uAgent.
The orchestrator module cannot be imported as `uagents_deploy.orchestrator_agent` because it
constructs an Agent and calls agent.include() at module scope. Instead we insert uagents_deploy/
onto sys.path so the bare imports inside the module resolve, then `import orchestrator_agent as ORCH`.

Test class map:
  - TestImportFix          (this plan, 2 tests)  — prereq import/ack fixes
  - TestTimeoutFallback    (this plan, 1 test)   — synchronous heuristic fallback
  - TestAckOrdering        (plan 02, 0 tests)    — ack-before-routing ordering with AsyncMock ctx
  - TestEvidenceMapping    (this plan, 1 test)   — DISPATCH-01 field mapping
  - TestSingleAgentDispatch (plan 02, 0 tests)   — single-agent fan-out replacement
  - TestUnwiredHandoff     (plan 02, 0 tests)    — politics/none unwired handoff
  - TestRationaleVisibility (this plan, 2 tests) — DISPATCH-04 rationale+tier in reply text
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# sys.path setup — mirrors tests/test_deployed_agent.py lines 14-21
# Makes `import orchestrator_agent` (and its bare `from router import ...`,
# `from protocols.messages import ...`) resolve without installing any package.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = REPO_ROOT / "uagents_deploy"

if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))

import orchestrator_agent as ORCH  # noqa: E402

# RouterDecision imported from the package for test fixture construction.
from uagents_deploy.router import RouterDecision  # noqa: E402

# Message types for plan 02 dispatch / handoff tests.
from uagents_deploy.protocols.messages import MarketRequest, EvidenceRequest  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers shared across test classes
# ---------------------------------------------------------------------------

def _make_decision(**kwargs) -> RouterDecision:
    """Build a RouterDecision with sensible defaults, overridable by kwargs."""
    defaults = dict(
        category="sports",
        target_agent_key="sports_video",
        rewritten_query="France World Cup 2026",
        protected_terms=["France", "2026"],
        confidence=0.9,
        rationale="World Cup is a sports event",
        tier="heuristic",
    )
    defaults.update(kwargs)
    return RouterDecision(**defaults)


# ============================================================================
# TestImportFix
# ============================================================================

class TestImportFix:
    """
    Prereq fixes that make handle_chat_message actually run (previously dead code).
    Task 1 (RED): CHAT_PROTOCOL_AVAILABLE is False with the broken uagents.chat import.
    Task 2 (GREEN): True after the fix to uagents_core.contrib.protocols.chat.
    """

    def test_chat_protocol_available(self):
        """CHAT_PROTOCOL_AVAILABLE must be True — proves uagents_core import path works
        and the @chat_protocol.on_message handler is actually registered."""
        assert ORCH.CHAT_PROTOCOL_AVAILABLE is True, (
            "CHAT_PROTOCOL_AVAILABLE is False — the chat import is still broken. "
            "Fix: change `from uagents.chat import ...` to "
            "`from uagents_core.contrib.protocols.chat import ...`"
        )

    def test_ack_has_msg_id(self):
        """ChatAcknowledgement(acknowledged_msg_id=<uuid>) must NOT raise.
        Proves the required field is supplied (previously constructed with no args -> ValidationError)."""
        # msg.msg_id comes back as a UUID from the Pydantic model — pass a real UUID.
        acknowledged_id = uuid4()
        # If this raises Pydantic ValidationError the prereq ack fix is missing.
        ack = ORCH.ChatAcknowledgement(acknowledged_msg_id=acknowledged_id)
        assert ack is not None


# ============================================================================
# TestTimeoutFallback
# ============================================================================

class TestTimeoutFallback:
    """
    Tests the synchronous heuristic fallback helper (SAFETY-03).
    This is the function called when asyncio.wait_for times out or the router raises.
    It must return a valid RouterDecision with no network access.
    """

    def test_timeout_yields_heuristic(self):
        """_heuristic_fallback('Will the Lakers beat the Celtics tonight?') must return
        a RouterDecision with tier='heuristic', category='sports', target='sports_video'.
        Proves the synchronous fallback path is wired and produces a usable decision."""
        decision = ORCH._heuristic_fallback("Will the Lakers beat the Celtics tonight?")
        assert decision.tier == "heuristic", f"Expected tier='heuristic', got {decision.tier!r}"
        assert decision.category == "sports", f"Expected category='sports', got {decision.category!r}"
        assert decision.target_agent_key == "sports_video", (
            f"Expected target_agent_key='sports_video', got {decision.target_agent_key!r}"
        )


# ============================================================================
# Plan 02 shared helpers
# ============================================================================

def _fake_ctx():
    """Return a minimal fake Context with AsyncMock send and MagicMock logger."""
    ctx = SimpleNamespace()
    ctx.send = AsyncMock()
    ctx.logger = MagicMock()
    return ctx


def _evidence_sends(ctx):
    """Return the ctx.send call_args_list entries whose payload is an EvidenceRequest."""
    return [c for c in ctx.send.call_args_list if isinstance(c.args[1], EvidenceRequest)]


def _make_market_request(**kwargs) -> MarketRequest:
    """Build a MarketRequest with sensible defaults, overridable by kwargs."""
    defaults = dict(
        market_id="mr-test-001",
        market_title="Test Market",
        market_question="France World Cup 2026",
        category="sports",
        protected_terms=["France", "2026"],
        resolution_criteria="TBD",
        current_yes_price=0.5,
        current_no_price=0.5,
    )
    defaults.update(kwargs)
    return MarketRequest(**defaults)


# ============================================================================
# TestAckOrdering  (plan 02)
# ============================================================================

class TestAckOrdering:
    """
    Verifies that the ChatAcknowledgement is sent BEFORE the router call fires
    (SAFETY-03 ordering). Uses AsyncMock ctx + monkeypatched router_route so no
    network or LLM call occurs.
    """

    def test_ack_before_route(self, monkeypatch):
        """First ctx.send call in handle_chat_message must be a ChatAcknowledgement.

        Approach: patch ORCH.router_route to return a fixed sports RouterDecision so
        no network/LLM occurs; build a ChatMessage with one TextContent; await the
        handler via asyncio.run; assert call_args_list[0] carries a ChatAcknowledgement.
        """
        from uagents_deploy.router import RouterDecision

        fixed_decision = RouterDecision(
            category="sports",
            target_agent_key="sports_video",
            rewritten_query="France World Cup 2026",
            protected_terms=["France", "2026"],
            confidence=0.9,
            rationale="sports tournament",
            tier="heuristic",
        )
        monkeypatch.setattr(ORCH, "router_route", lambda q: fixed_decision)

        ctx = _fake_ctx()
        msg = ORCH.ChatMessage(
            content=[ORCH.TextContent(text="Will the Lakers beat the Celtics tonight?")]
        )

        asyncio.run(ORCH.handle_chat_message(ctx, "agent1qsender", msg))

        # The very first ctx.send must be a ChatAcknowledgement (ack before route)
        assert ctx.send.call_args_list, "ctx.send was never called"
        first_payload = ctx.send.call_args_list[0].args[1]
        assert isinstance(first_payload, ORCH.ChatAcknowledgement), (
            f"Expected ChatAcknowledgement as first send, got {type(first_payload).__name__!r}"
        )


# ============================================================================
# TestEvidenceMapping
# ============================================================================

class TestEvidenceMapping:
    """
    DISPATCH-01: RouterDecision maps onto existing MarketRequest / EvidenceRequest fields
    with NO protocol change.
    """

    def test_dispatch01_field_mapping(self):
        """_build_market_request_from_decision maps:
          decision.rewritten_query -> MarketRequest.market_question
          decision.category        -> MarketRequest.category
          decision.protected_terms -> MarketRequest.protected_terms
        And EvidenceRequest round-trips the three fields unchanged."""
        decision = _make_decision(
            category="sports",
            target_agent_key="sports_video",
            rewritten_query="France World Cup 2026",
            protected_terms=["France", "2026"],
            confidence=0.9,
            rationale="sports tournament",
            tier="heuristic",
        )
        user_text = "Will France win the World Cup 2026?"

        mr = ORCH._build_market_request_from_decision(user_text, decision)

        # DISPATCH-01 field mapping
        assert mr.market_question == "France World Cup 2026", (
            f"Expected market_question='France World Cup 2026', got {mr.market_question!r}"
        )
        assert mr.category == "sports", f"Expected category='sports', got {mr.category!r}"
        assert mr.protected_terms == ["France", "2026"], (
            f"Expected protected_terms=['France', '2026'], got {mr.protected_terms!r}"
        )
        assert mr.market_title.startswith("Will France"), (
            f"Expected market_title to start with 'Will France', got {mr.market_title!r}"
        )

        # EvidenceRequest round-trip — no protocol change
        from protocols.messages import EvidenceRequest  # bare import (DEPLOY_DIR on path)
        er = EvidenceRequest(
            market_question=mr.market_question,
            category=mr.category,
            protected_terms=mr.protected_terms,
        )
        assert er.market_question == mr.market_question
        assert er.category == mr.category
        assert er.protected_terms == mr.protected_terms


# ============================================================================
# TestSingleAgentDispatch  (plan 02)
# ============================================================================

class TestSingleAgentDispatch:
    """
    DISPATCH-02: handle_market_request must dispatch to exactly ONE chosen agent
    (keyed by CATEGORY_TO_AGENT[msg.category] -> AGENT_ADDRESSES[target_key]),
    not fan out to all three.
    """

    def test_single_send_to_sports(self, monkeypatch):
        """Exactly ONE EvidenceRequest is sent to the sports_video address."""
        monkeypatch.setitem(ORCH.AGENT_ADDRESSES, "sports_video", "agent1qSPORTS")

        mr = _make_market_request(category="sports")
        ctx = _fake_ctx()

        asyncio.run(ORCH.handle_market_request(ctx, "agent1qsender", mr))

        ev_sends = _evidence_sends(ctx)
        assert len(ev_sends) == 1, (
            f"Expected exactly 1 EvidenceRequest send, got {len(ev_sends)}"
        )
        assert ev_sends[0].args[0] == "agent1qSPORTS", (
            f"EvidenceRequest sent to wrong address: {ev_sends[0].args[0]!r}"
        )

        state = ORCH.analysis_state.get(str(mr.msg_id))
        assert state is not None, "No analysis_state entry for this msg_id"
        assert state.pending_agents == 1, (
            f"Expected pending_agents=1, got {state.pending_agents}"
        )
        assert state.agents_used == ["sports_video"], (
            f"Expected agents_used=['sports_video'], got {state.agents_used!r}"
        )

    def test_no_fan_out(self, monkeypatch):
        """With all addresses set, exactly ONE EvidenceRequest is sent (no 3-way fan-out)."""
        monkeypatch.setitem(ORCH.AGENT_ADDRESSES, "sports_video", "agent1qSPORTS")
        monkeypatch.setitem(ORCH.AGENT_ADDRESSES, "financial_research", "agent1qFIN")
        monkeypatch.setitem(ORCH.AGENT_ADDRESSES, "culture_web", "agent1qCULT")

        mr = _make_market_request(category="sports")
        ctx = _fake_ctx()

        asyncio.run(ORCH.handle_market_request(ctx, "agent1qsender", mr))

        ev_sends = _evidence_sends(ctx)
        assert len(ev_sends) == 1, (
            f"Fan-out NOT eliminated — expected 1 EvidenceRequest send, got {len(ev_sends)}"
        )
        sent_addrs = [c.args[0] for c in ev_sends]
        assert "agent1qFIN" not in sent_addrs, "EvidenceRequest incorrectly sent to financial_research"
        assert "agent1qCULT" not in sent_addrs, "EvidenceRequest incorrectly sent to culture_web"


# ============================================================================
# TestUnwiredHandoff  (plan 02)
# ============================================================================

class TestUnwiredHandoff:
    """
    DISPATCH-03: when the chosen category has no wired address (politics/none),
    or the address env var is unset, the orchestrator sends a clear
    "no live agent wired yet" ChatMessage + EndSessionContent to the requester,
    pops analysis_state[msg_id] (no stale pending-agents hang), and does NOT
    send any EvidenceRequest.
    """

    def _find_text_content_sends(self, ctx):
        """Return ChatMessage sends whose content contains a TextContent."""
        results = []
        for c in ctx.send.call_args_list:
            payload = c.args[1]
            if isinstance(payload, ORCH.ChatMessage):
                for item in payload.content:
                    if isinstance(item, ORCH.TextContent):
                        results.append(item.text)
                        break
        return results

    def _find_end_session_sends(self, ctx):
        """Return ChatMessage sends whose content contains EndSessionContent."""
        results = []
        for c in ctx.send.call_args_list:
            payload = c.args[1]
            if isinstance(payload, ORCH.ChatMessage):
                for item in payload.content:
                    if isinstance(item, ORCH.EndSessionContent):
                        results.append(payload)
                        break
        return results

    def test_politics_clean_handoff(self):
        """category='politics' -> handoff text + EndSessionContent, NO EvidenceRequest."""
        mr = _make_market_request(category="politics", market_question="Who wins the senate?")
        ctx = _fake_ctx()

        asyncio.run(ORCH.handle_market_request(ctx, "agent1qsender", mr))

        ev_sends = _evidence_sends(ctx)
        assert len(ev_sends) == 0, (
            f"Expected NO EvidenceRequest for politics, got {len(ev_sends)}"
        )

        text_sends = self._find_text_content_sends(ctx)
        assert any("no live agent wired yet" in t for t in text_sends), (
            f"Expected 'no live agent wired yet' in a ChatMessage TextContent; got: {text_sends!r}"
        )

        end_sends = self._find_end_session_sends(ctx)
        assert len(end_sends) >= 1, "Expected at least one EndSessionContent ChatMessage"

    def test_unset_address_handoff(self, monkeypatch):
        """category='sports' with AGENT_ADDRESSES['sports_video']=None -> clean handoff."""
        monkeypatch.setitem(ORCH.AGENT_ADDRESSES, "sports_video", None)

        mr = _make_market_request(category="sports")
        ctx = _fake_ctx()

        asyncio.run(ORCH.handle_market_request(ctx, "agent1qsender", mr))

        ev_sends = _evidence_sends(ctx)
        assert len(ev_sends) == 0, (
            f"Expected NO EvidenceRequest when address is None, got {len(ev_sends)}"
        )

        text_sends = self._find_text_content_sends(ctx)
        assert any("no live agent wired yet" in t for t in text_sends), (
            f"Expected 'no live agent wired yet' in a ChatMessage; got: {text_sends!r}"
        )

        end_sends = self._find_end_session_sends(ctx)
        assert len(end_sends) >= 1, "Expected EndSessionContent ChatMessage"

    def test_analysis_state_cleared(self):
        """category='politics' -> analysis_state entry is popped (no pending_agents==0 hang)."""
        mr = _make_market_request(category="politics")
        ctx = _fake_ctx()

        asyncio.run(ORCH.handle_market_request(ctx, "agent1qsender", mr))

        assert str(mr.msg_id) not in ORCH.analysis_state, (
            "analysis_state still contains stale entry after unwired handoff — "
            "pending_agents==0 forever-hang NOT guarded"
        )


# ============================================================================
# TestRationaleVisibility
# ============================================================================

class TestRationaleVisibility:
    """
    DISPATCH-04: the routing decision rationale and tier must be visible in the
    chat reply text so judges can observe how routing decisions were made.
    """

    def test_rationale_in_reply(self):
        """_format_routing_note(decision) must include decision.rationale as a substring."""
        decision = _make_decision(rationale="World Cup is a sports event", tier="heuristic")
        note = ORCH._format_routing_note(decision)
        assert "World Cup is a sports event" in note, (
            f"Expected rationale substring in routing note, got: {note!r}"
        )

    def test_tier_in_reply(self):
        """_format_routing_note(decision) must include decision.tier ('heuristic') as a substring."""
        decision = _make_decision(tier="heuristic")
        note = ORCH._format_routing_note(decision)
        assert "heuristic" in note, (
            f"Expected 'heuristic' in routing note, got: {note!r}"
        )
