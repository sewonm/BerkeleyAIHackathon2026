"""
Tests for the SportsAgent sync core (app/agents/sports_video_agent.py).

These tests verify:
- SportsVideoAgent is importable and constructible with no args
- run() returns >= 2 EvidenceChunk items
- Every chunk has source_type == "sports_video"
- Every chunk has the four required metadata keys
- Coordinator compat: SportsVideoAgent = SportsAgent alias works
- get_sports_agent_seed() returns expected default or env override
"""

import os
import pytest
from app.schemas.market import Market


@pytest.fixture
def sports_market():
    """A typical sports market for testing."""
    return Market(
        market_id="wc2026-arg-win",
        title="2026 FIFA World Cup - Argentina to Win",
        question="Will Argentina win the 2026 FIFA World Cup?",
        category="sports",
        resolution_criteria="Resolves YES if Argentina wins the 2026 FIFA World Cup final.",
        protected_terms=["Argentina", "World Cup", "2026"],
    )


# ---------------------------------------------------------------------------
# Import & construction
# ---------------------------------------------------------------------------

class TestSportsVideoAgentImport:
    """SportsVideoAgent must be importable and constructible with no args."""

    def test_import_sports_video_agent(self):
        from app.agents.sports_video_agent import SportsVideoAgent  # noqa: F401

    def test_construct_no_args(self):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        assert agent is not None

    def test_is_base_agent_subclass(self):
        from app.agents.sports_video_agent import SportsVideoAgent
        from app.agents.base_agent import BaseAgent
        agent = SportsVideoAgent()
        assert isinstance(agent, BaseAgent)

    def test_alias_is_sports_agent(self):
        """SportsVideoAgent should be an alias for SportsAgent (or be directly named SportsVideoAgent)."""
        from app.agents.sports_video_agent import SportsVideoAgent, SportsAgent
        assert SportsVideoAgent is SportsAgent


# ---------------------------------------------------------------------------
# run() return contract
# ---------------------------------------------------------------------------

class TestSportsVideoAgentRun:
    """run() must return >= 2 EvidenceChunk items."""

    def test_run_returns_list(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        assert isinstance(result, list)

    def test_run_returns_at_least_two_chunks(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        assert len(result) >= 2, f"Expected >= 2 chunks, got {len(result)}"

    def test_all_chunks_source_type_sports_video(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        for chunk in result:
            assert chunk.source_type == "sports_video", (
                f"Expected source_type='sports_video', got {chunk.source_type!r}"
            )

    def test_all_chunks_have_text(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        for chunk in result:
            assert chunk.text, "Each chunk must have non-empty text"

    def test_all_chunks_have_required_metadata_keys(self, sports_market):
        """Each chunk metadata must contain: kind, fetched_via, source_strength, observed_at."""
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        required_keys = {"kind", "fetched_via", "source_strength", "observed_at"}
        for i, chunk in enumerate(result):
            missing = required_keys - set(chunk.metadata)
            assert not missing, (
                f"Chunk {i} missing metadata keys: {missing}. Got: {set(chunk.metadata)}"
            )

    def test_all_chunks_fetched_via_is_stub(self, sports_market):
        """fetched_via must equal 'stub' (phase 1 stub bundle)."""
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        for i, chunk in enumerate(result):
            assert chunk.metadata.get("fetched_via") == "stub", (
                f"Chunk {i}: expected fetched_via='stub', got {chunk.metadata.get('fetched_via')!r}"
            )

    def test_chunks_have_distinct_text(self, sports_market):
        """The stub bundle must have distinct (non-identical) chunks."""
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        texts = [c.text for c in result]
        assert len(set(texts)) >= 2, "At least 2 distinct text values required"

    def test_chunks_have_stub_source_url(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        for chunk in result:
            assert chunk.source_url is not None

    def test_chunks_have_confidence(self, sports_market):
        from app.agents.sports_video_agent import SportsVideoAgent
        agent = SportsVideoAgent()
        result = agent.run(sports_market)
        for chunk in result:
            assert chunk.confidence is not None and 0.0 <= chunk.confidence <= 1.0


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------

class TestGetSportsAgentSeed:
    """get_sports_agent_seed() must export and return the env-override or default."""

    def test_import_seed_helper(self):
        from app.agents.sports_video_agent import get_sports_agent_seed  # noqa: F401

    def test_import_default_seed_constant(self):
        from app.agents.sports_video_agent import DEFAULT_SPORTS_AGENT_SEED
        assert isinstance(DEFAULT_SPORTS_AGENT_SEED, str) and DEFAULT_SPORTS_AGENT_SEED

    def test_seed_helper_returns_default_when_env_not_set(self):
        from app.agents.sports_video_agent import get_sports_agent_seed, DEFAULT_SPORTS_AGENT_SEED
        env_key = "SPORTS_VIDEO_AGENT_SEED"
        # Ensure env var is unset
        original = os.environ.pop(env_key, None)
        try:
            result = get_sports_agent_seed()
            assert result == DEFAULT_SPORTS_AGENT_SEED
        finally:
            if original is not None:
                os.environ[env_key] = original

    def test_seed_helper_reads_env_override(self):
        from app.agents.sports_video_agent import get_sports_agent_seed
        env_key = "SPORTS_VIDEO_AGENT_SEED"
        test_seed = "test-override-seed-12345"
        original = os.environ.get(env_key)
        os.environ[env_key] = test_seed
        try:
            result = get_sports_agent_seed()
            assert result == test_seed
        finally:
            if original is None:
                del os.environ[env_key]
            else:
                os.environ[env_key] = original


# ---------------------------------------------------------------------------
# Coordinator compat
# ---------------------------------------------------------------------------

class TestCoordinatorCompat:
    """Coordinator must be able to use sports_agent.run(market) unchanged."""

    def test_coordinator_sports_agent_is_sports_video_agent(self):
        from app.agents.coordinator import Coordinator
        from app.agents.sports_video_agent import SportsVideoAgent
        c = Coordinator()
        assert isinstance(c.sports_agent, SportsVideoAgent)

    def test_coordinator_sports_agent_run_returns_chunks(self, sports_market):
        from app.agents.coordinator import Coordinator
        c = Coordinator()
        result = c.sports_agent.run(sports_market)
        assert len(result) >= 2
        assert all(e.source_type == "sports_video" for e in result)
        assert all(
            {"kind", "fetched_via", "source_strength", "observed_at"} <= set(e.metadata)
            for e in result
        )
