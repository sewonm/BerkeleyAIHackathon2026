"""
Offline/keyless test suite for uagents_deploy.router.

All tests are OFFLINE and KEYLESS — no network, no real API keys, no LLM calls.
The LLM tier (_route_llm) is a stub returning None in plan 01; TestHeuristic
calls _route_heuristic() directly to bypass the ladder entirely.

Classes:
  TestImportable       — module imports cleanly with no key/SDK/network (TEST-01)
  TestRouteOutput      — route() return contract (ROUTE-01..05)
  TestProtectedTerms   — year extraction + protected_terms (PROMPT-03)
  TestHeuristic        — SAFETY-02 golden cases via _route_heuristic() directly
"""

import importlib
import pytest

import uagents_deploy.router as router_module
from uagents_deploy.router import (
    route,
    RouterDecision,
    VALID_CATEGORIES,
    CATEGORY_TO_AGENT,
    REJECT_FLOOR,
    _route_heuristic,
    _extract_years,
)


# ---------------------------------------------------------------------------
# class TestImportable
# ---------------------------------------------------------------------------

class TestImportable:
    """Module-level import discipline — TEST-01."""

    def test_import_no_network(self):
        """import uagents_deploy.router succeeds with no uagents/SDK/key needed."""
        # The module is already imported above; reimport to confirm it is idempotent.
        mod = importlib.import_module("uagents_deploy.router")
        assert mod is not None
        # Verify no uagents dependency was pulled in
        assert hasattr(mod, "RouterDecision")
        assert hasattr(mod, "route")
        assert hasattr(mod, "VALID_CATEGORIES")

    def test_keyless_no_raise(self, monkeypatch):
        """With ASI1_API_KEY unset, route() returns a RouterDecision without raising."""
        monkeypatch.delenv("ASI1_API_KEY", raising=False)
        result = route("Will the Lakers beat the Celtics tonight?")
        assert isinstance(result, RouterDecision)


# ---------------------------------------------------------------------------
# class TestRouteOutput
# ---------------------------------------------------------------------------

class TestRouteOutput:
    """route() return contract — ROUTE-01..05."""

    def test_category_in_valid_set(self):
        """route(q).category is always in VALID_CATEGORIES."""
        questions = [
            "Will the Lakers beat the Celtics tonight?",
            "Will Bitcoin hit $100k?",
            "Will France win the World Cup 2026?",
            "asdfgh qwerty 123",
        ]
        for q in questions:
            result = route(q)
            assert result.category in VALID_CATEGORIES, (
                f"category {result.category!r} not in VALID_CATEGORIES for q={q!r}"
            )

    def test_confidence_range(self):
        """route(q).confidence is always in [0.0, 1.0]."""
        questions = [
            "Will France win the World Cup 2026?",
            "Will Bitcoin hit $100k?",
            "asdfgh qwerty 123",
        ]
        for q in questions:
            result = route(q)
            assert 0.0 <= result.confidence <= 1.0, (
                f"confidence {result.confidence} out of range for q={q!r}"
            )

    def test_reject_floor(self):
        """A question with no strong keywords routes to category='none'."""
        result = route("asdfgh qwerty 123")
        assert result.category == "none"

    def test_target_agent_key(self):
        """Sports question -> target_agent_key='sports_video'; politics -> None."""
        sports_result = route("Will the Lakers beat the Celtics tonight?")
        assert sports_result.target_agent_key == "sports_video"

        politics_result = route("Will the party that wins the election control the Senate?")
        assert politics_result.target_agent_key is None

    def test_rationale_nonempty(self):
        """route(q).rationale is always a non-empty string."""
        questions = [
            "Will France win the World Cup 2026?",
            "asdfgh qwerty 123",
        ]
        for q in questions:
            result = route(q)
            assert isinstance(result.rationale, str)
            assert len(result.rationale) > 0, f"rationale is empty for q={q!r}"


# ---------------------------------------------------------------------------
# class TestProtectedTerms
# ---------------------------------------------------------------------------

class TestProtectedTerms:
    """Year extraction and protected_terms contract — PROMPT-03."""

    def test_years_extracted(self):
        """_extract_years and route() both capture 4-digit 20xx years."""
        # Direct function check
        years = _extract_years("Will France win the World Cup 2026?")
        assert years == ["2026"]

        # End-to-end through route()
        result = route("Will France win the World Cup 2026?")
        assert "2026" in result.protected_terms


# ---------------------------------------------------------------------------
# class TestHeuristic
# ---------------------------------------------------------------------------

class TestHeuristic:
    """SAFETY-02 golden cases — call _route_heuristic() directly to bypass LLM ladder."""

    def test_politics_routing(self):
        """election + Senate keywords -> politics (not sports)."""
        result = _route_heuristic(
            "Will the party that wins the election control the Senate?"
        )
        assert result.category == "politics", (
            f"Expected 'politics', got {result.category!r}"
        )

    def test_financial_routing(self):
        """bitcoin + $100k -> financial (not sports)."""
        result = _route_heuristic("Will Bitcoin hit $100k?")
        assert result.category == "financial", (
            f"Expected 'financial', got {result.category!r}"
        )

    def test_sports_routing(self):
        """world cup -> sports (world cup=3.0 beats win=0.5)."""
        result = _route_heuristic("Will France win the World Cup 2026?")
        assert result.category == "sports", (
            f"Expected 'sports', got {result.category!r}"
        )

    def test_politics_shutdown(self):
        """government shutdown -> politics."""
        result = _route_heuristic("Will a government shutdown happen before October?")
        assert result.category == "politics", (
            f"Expected 'politics', got {result.category!r}"
        )

    def test_ood_none(self):
        """Weather/gibberish -> none (no recognizable keywords)."""
        weather_result = _route_heuristic("What's the weather in Paris tomorrow?")
        assert weather_result.category == "none", (
            f"Expected 'none' for weather question, got {weather_result.category!r}"
        )

        gibberish_result = _route_heuristic("asdfgh qwerty 123")
        assert gibberish_result.category == "none", (
            f"Expected 'none' for gibberish, got {gibberish_result.category!r}"
        )
