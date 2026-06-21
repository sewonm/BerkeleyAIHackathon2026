"""
Phase 2 — ESPN HTTP anchor tests (deterministic, offline, fixture-backed).

These verify the live collection LOGIC without touching the network:
- the collector turns recorded ESPN JSON into normalized EvidenceChunks,
- the sport abstraction is config-only (SA-DATA-06),
- output is deterministic across runs (success criterion 3),
- the two validated sports (World Cup soccer + MLB) both produce anchor chunks.

Fixtures live in tests/fixtures/espn/ (refresh with scripts/record_espn_fixtures.py).
"""

from pathlib import Path

import pytest

from app.schemas.evidence import EvidenceChunk
from app.schemas.market import Market
from app.services.espn import (
    SPORT_REGISTRY,
    ESPNClient,
    collect_espn_evidence,
    resolve_sport,
    get_sport_config,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "espn"
REQUIRED_METADATA = {
    "kind", "fetched_via", "sport", "source_strength",
    "observed_at", "league", "event_id",
}
FIXED_TS = "2026-06-20T00:00:00Z"

# Only the sports we ship fixtures for are exercised end-to-end here.
FIXTURED_SPORTS = ["soccer", "baseball"]


def _client() -> ESPNClient:
    """Offline, fixtures-only client (a miss returns None, never the network)."""
    return ESPNClient(fixtures_dir=FIXTURES_DIR, offline=True)


def _collect(sport: str) -> list[EvidenceChunk]:
    market = Market(
        market_id=f"t-{sport}", title=sport, question=sport,
        category="sports", resolution_criteria="n/a",
    )
    return collect_espn_evidence(
        market, client=_client(), sport=sport, observed_at=FIXED_TS
    )


# ---------------------------------------------------------------------------
# Fixtures sanity
# ---------------------------------------------------------------------------

def test_fixtures_present():
    files = list(FIXTURES_DIR.glob("*.json"))
    assert files, (
        "No ESPN fixtures found. Run: python scripts/record_espn_fixtures.py"
    )


# ---------------------------------------------------------------------------
# Per-sport collection contract (SA-DATA-01..05, SA-OUT-01)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sport", FIXTURED_SPORTS)
class TestCollectionContract:

    def test_returns_chunks(self, sport):
        chunks = _collect(sport)
        assert len(chunks) >= 4, f"{sport}: expected >= 4 chunks, got {len(chunks)}"

    def test_all_sports_video_source_type(self, sport):
        for c in _collect(sport):
            assert c.source_type == "sports_video"

    def test_all_chunks_nonempty_text(self, sport):
        for c in _collect(sport):
            assert c.text and c.text.strip()

    def test_metadata_contract(self, sport):
        for c in _collect(sport):
            missing = REQUIRED_METADATA - set(c.metadata)
            assert not missing, f"{sport} {c.metadata.get('kind')}: missing {missing}"
            assert c.metadata["fetched_via"] == "http"
            assert c.metadata["source_strength"] == "anchor"
            assert c.metadata["sport"] == sport

    def test_has_score_state(self, sport):
        kinds = {c.metadata["kind"] for c in _collect(sport)}
        assert "score_state" in kinds  # SA-DATA-01

    def test_has_odds_with_line_movement(self, sport):
        odds = [c for c in _collect(sport) if c.metadata["kind"] == "odds"]
        assert odds, f"{sport}: no odds chunk (SA-DATA-03)"
        assert "Line movement" in odds[0].text  # open/close/current

    def test_has_probability(self, sport):
        kinds = {c.metadata["kind"] for c in _collect(sport)}
        assert "win_probability" in kinds  # SA-DATA-04 (model and/or implied)

    def test_has_availability(self, sport):
        # SA-DATA-05 — injuries and/or lineups (ESPN exposes >= 1 per sport)
        kinds = {c.metadata["kind"] for c in _collect(sport)}
        assert kinds & {"injuries", "lineups"}


# ---------------------------------------------------------------------------
# Determinism (success criterion 3)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sport", FIXTURED_SPORTS)
def test_deterministic_across_runs(sport):
    a = _collect(sport)
    b = _collect(sport)
    assert len(a) == len(b)
    sig_a = [(c.metadata["kind"], c.text, c.source_url) for c in a]
    sig_b = [(c.metadata["kind"], c.text, c.source_url) for c in b]
    assert sig_a == sig_b, f"{sport}: collection is not deterministic across runs"


# ---------------------------------------------------------------------------
# Coverage across the two validated sports (success criterion 2 + 4)
# ---------------------------------------------------------------------------

def test_two_sports_cover_all_data_kinds():
    kinds = set()
    for sport in FIXTURED_SPORTS:
        kinds |= {c.metadata["kind"] for c in _collect(sport)}
    expected = {"score_state", "box_stats", "event_log", "odds", "win_probability"}
    missing = expected - kinds
    assert not missing, f"across soccer+MLB, missing kinds: {missing}"
    assert kinds & {"injuries", "lineups"}  # SA-DATA-05 present somewhere


# ---------------------------------------------------------------------------
# Sport abstraction is config-only (SA-DATA-06)
# ---------------------------------------------------------------------------

class TestRegistryConfigOnly:

    def test_known_sports_registered(self):
        for key in ("soccer", "baseball", "basketball", "football"):
            assert key in SPORT_REGISTRY

    def test_slug_format(self):
        assert get_sport_config("soccer").slug == "soccer/fifa.world"
        assert get_sport_config("baseball").slug == "baseball/mlb"
        assert get_sport_config("basketball").slug == "basketball/nba"
        assert get_sport_config("football").slug == "football/nfl"

    @pytest.mark.parametrize("text,expected", [
        ("Will Argentina win the 2026 FIFA World Cup?", "soccer"),
        ("Will the Yankees make the MLB playoffs? baseball", "baseball"),
        ("Will the Lakers win the NBA finals?", "basketball"),
        ("Who wins the Super Bowl this NFL season?", "football"),
    ])
    def test_resolve_sport_from_market_text(self, text, expected):
        market = Market(
            market_id="r", title=text, question=text,
            category="sports", resolution_criteria="n/a",
        )
        assert resolve_sport(market).key == expected

    def test_unknown_market_falls_back_to_default(self):
        market = Market(
            market_id="r", title="Will it rain tomorrow?",
            question="Will it rain tomorrow?", category="weather",
            resolution_criteria="n/a",
        )
        # No sport keyword -> default sport (soccer showcase), never crashes.
        assert resolve_sport(market).key in SPORT_REGISTRY


# ---------------------------------------------------------------------------
# Graceful failure
# ---------------------------------------------------------------------------

def test_empty_when_offline_without_fixtures(tmp_path):
    """No fixtures + hard offline -> empty list, never an exception."""
    client = ESPNClient(fixtures_dir=tmp_path, offline=True)
    market = Market(
        market_id="x", title="mlb", question="mlb",
        category="sports", resolution_criteria="n/a",
    )
    assert collect_espn_evidence(market, client=client, sport="baseball") == []


# ---------------------------------------------------------------------------
# Agent live path (SportsAgent.run uses ESPN, driven by env-configured fixtures)
# ---------------------------------------------------------------------------

class TestSportsAgentLivePath:
    """run() takes the live ESPN path when not forced offline."""

    def test_run_returns_http_chunks_from_fixtures(self, monkeypatch):
        # Live path on; ESPN client reads fixtures offline via env. Noisy layer
        # forced offline (no fixtures) so the bundle is anchor-only -> all http.
        monkeypatch.delenv("SPORTS_AGENT_OFFLINE", raising=False)
        monkeypatch.setenv("ESPN_FIXTURES_DIR", str(FIXTURES_DIR))
        monkeypatch.setenv("ESPN_OFFLINE", "1")
        monkeypatch.setenv("BROWSERBASE_OFFLINE", "1")

        from app.agents.sports_video_agent import SportsVideoAgent

        market = Market(
            market_id="wc", title="2026 FIFA World Cup soccer",
            question="Will the World Cup match go over? soccer fifa",
            category="sports", resolution_criteria="n/a",
        )
        chunks = SportsVideoAgent().run(market)
        assert len(chunks) >= 2
        assert all(c.metadata.get("fetched_via") == "http" for c in chunks)
        assert all(c.source_type == "sports_video" for c in chunks)

    def test_run_falls_back_to_stub_when_no_data(self, monkeypatch, tmp_path):
        # Live path on, but fixtures dir is empty + offline -> stub fallback.
        monkeypatch.delenv("SPORTS_AGENT_OFFLINE", raising=False)
        monkeypatch.setenv("ESPN_FIXTURES_DIR", str(tmp_path))
        monkeypatch.setenv("ESPN_OFFLINE", "1")
        monkeypatch.setenv("BROWSERBASE_OFFLINE", "1")

        from app.agents.sports_video_agent import SportsVideoAgent

        market = Market(
            market_id="wc", title="soccer world cup",
            question="soccer world cup", category="sports",
            resolution_criteria="n/a",
        )
        chunks = SportsVideoAgent().run(market)
        assert len(chunks) >= 2
        assert all(c.metadata.get("fetched_via") == "stub" for c in chunks)
