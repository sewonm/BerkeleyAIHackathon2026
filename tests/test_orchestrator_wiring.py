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

import sys
from pathlib import Path
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
# TestAckOrdering  (plan 02 — placeholder, not authored here)
# ============================================================================

class TestAckOrdering:
    """
    Plan 02 will add tests verifying ACK is sent before the router call.
    Requires AsyncMock ctx — authored in plan 02 alongside the dispatch helper.
    """


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
# TestSingleAgentDispatch  (plan 02 — placeholder, not authored here)
# ============================================================================

class TestSingleAgentDispatch:
    """
    Plan 02 will add tests verifying single-agent dispatch replaces the fan-out.
    Authored in plan 02 alongside the dispatch helper.
    """


# ============================================================================
# TestUnwiredHandoff  (plan 02 — placeholder, not authored here)
# ============================================================================

class TestUnwiredHandoff:
    """
    Plan 02 will add tests verifying the politics/none unwired handoff behavior.
    Authored in plan 02 alongside the dispatch helper.
    """


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
