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
  TestLLMTier          — LLM tier mocked; validates rewrite/category/tier (PROMPT-01/02)
  TestFallback         — every demotion path; route() never raises (SAFETY-01)
"""

import importlib
import pytest
from unittest.mock import MagicMock, patch

import uagents_deploy.router as router_module
from uagents_deploy.router import (
    route,
    RouterDecision,
    VALID_CATEGORIES,
    CATEGORY_TO_AGENT,
    REJECT_FLOOR,
    _route_heuristic,
    _extract_years,
    _protected_term_postcheck,
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


# ---------------------------------------------------------------------------
# Helper — build a mock LLMService instance
# ---------------------------------------------------------------------------

def _mock_svc(available=True, ok=True, data=None, error=""):
    """Return a MagicMock LLMService instance with .available and .chat_json configured."""
    svc = MagicMock()
    svc.available = available
    svc.chat_json.return_value = MagicMock(
        ok=ok,
        data=data if data is not None else {},
        error=error,
        provider="asi1",
    )
    return svc


# ---------------------------------------------------------------------------
# class TestLLMTier — mocked chat_json returns valid in-enum dict
# ---------------------------------------------------------------------------

class TestLLMTier:
    """LLM tier produces tier='llm' RouterDecision when mock returns valid dict (PROMPT-01/02)."""

    def test_rewrite_strips_framing(self):
        """LLM rewrite strips 'Will...?'/framing; route() -> tier='llm', category='sports'."""
        mock_data = {
            "category": "sports",
            "confidence": 0.95,
            "rewritten_query": "France World Cup 2026 performance",
            "protected_terms": ["France", "World Cup", "2026"],
            "rationale": "sports tournament",
        }
        svc = _mock_svc(available=True, ok=True, data=mock_data)

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will France win the World Cup 2026?")

        assert decision.category == "sports"
        assert decision.target_agent_key == "sports_video"
        assert decision.tier == "llm"
        # Rewrite must NOT contain "Will" or end with "?"
        assert "Will" not in decision.rewritten_query
        assert not decision.rewritten_query.endswith("?")
        # Protected terms must contain the expected entities
        assert "France" in decision.protected_terms
        assert "2026" in decision.protected_terms

    def test_per_category_rewrite(self):
        """Financial LLM rewrite flows through unchanged when post-check passes."""
        mock_data = {
            "category": "financial",
            "confidence": 0.90,
            "rewritten_query": "Bitcoin price 100000 2026 outlook",
            "protected_terms": ["Bitcoin", "2026"],
            "rationale": "crypto price question",
        }
        svc = _mock_svc(available=True, ok=True, data=mock_data)

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will Bitcoin hit $100k by end of 2026?")

        # Post-check should pass: "Bitcoin" and "2026" both appear in rewritten_query
        assert decision.rewritten_query == "Bitcoin price 100000 2026 outlook"
        assert decision.tier == "llm"


# ---------------------------------------------------------------------------
# class TestProtectedTerms — extended with post-check fallback
# (test_years_extracted from plan-01 already in the class above)
# ---------------------------------------------------------------------------

class TestProtectedTermsPostcheck:
    """Post-check fallback — PROMPT-04 forward-raw on missing protected term."""

    def test_postcheck_fallback(self):
        """Dropped protected term -> rewritten_query falls back to raw question."""
        raw_question = "Will France win the World Cup 2026?"
        mock_data = {
            "category": "sports",
            "confidence": 0.88,
            "rewritten_query": "FIFA tournament",  # missing "France", "World Cup", "2026"
            "protected_terms": ["France", "2026"],
            "rationale": "soccer event",
        }
        svc = _mock_svc(available=True, ok=True, data=mock_data)

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route(raw_question)

        # Post-check fails (rewrite dropped "France" and "2026") -> raw question forwarded
        assert decision.rewritten_query == raw_question
        # Category is still the LLM's result
        assert decision.category == "sports"

    def test_postcheck_passes_on_all_terms_present(self):
        """_protected_term_postcheck returns True when all terms present (case-insensitive)."""
        assert _protected_term_postcheck("France World Cup 2026", {"World Cup", "2026"}) is True
        assert _protected_term_postcheck("france world cup 2026", {"World Cup", "2026"}) is True

    def test_postcheck_fails_on_missing_term(self):
        """_protected_term_postcheck returns False when any term is absent."""
        assert _protected_term_postcheck("FIFA tournament", {"World Cup", "2026"}) is False
        assert _protected_term_postcheck("France 2026 tournament", {"World Cup", "2026"}) is False


# ---------------------------------------------------------------------------
# class TestFallback — every demotion path; route() never raises (SAFETY-01)
# ---------------------------------------------------------------------------

class TestFallback:
    """Every LLM demotion path falls to heuristic and route() never raises (SAFETY-01)."""

    def test_llm_unavailable_uses_heuristic(self):
        """mock ok=False -> route() falls to heuristic tier."""
        svc = _mock_svc(available=True, ok=False, error="api error")

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will France win the World Cup 2026?")

        assert decision.tier == "heuristic"
        assert isinstance(decision, RouterDecision)

    def test_no_key_uses_heuristic(self):
        """mock available=False -> chat_json NOT called -> heuristic tier."""
        svc = _mock_svc(available=False)

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will the Lakers beat the Celtics tonight?")

        svc.chat_json.assert_not_called()
        assert decision.tier == "heuristic"
        assert isinstance(decision, RouterDecision)

    def test_llm_exception_no_raise(self):
        """chat_json raises RuntimeError -> route() does NOT raise, returns heuristic."""
        svc = _mock_svc(available=True)
        svc.chat_json.side_effect = RuntimeError("boom")

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will Bitcoin hit $100k?")

        assert isinstance(decision, RouterDecision)
        assert decision.tier == "heuristic"

    def test_invalid_enum_demotes(self):
        """LLM returns invalid category 'Crypto' -> demote to heuristic tier."""
        mock_data = {
            "category": "Crypto",  # not in VALID_CATEGORIES
            "confidence": 0.90,
            "rewritten_query": "crypto price 2026",
            "protected_terms": ["Bitcoin"],
            "rationale": "crypto question",
        }
        svc = _mock_svc(available=True, ok=True, data=mock_data)

        with patch("uagents_deploy.router.LLMService", return_value=svc):
            decision = route("Will Bitcoin hit $100k by end of 2026?")

        # _validate_and_build returns None for invalid enum -> falls to heuristic
        assert decision.tier == "heuristic"
        assert decision.category in VALID_CATEGORIES
