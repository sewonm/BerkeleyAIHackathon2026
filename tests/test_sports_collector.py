"""
Phase 4 — merged, query-aware sports collector tests (offline, fixture-backed).

Verifies the agent's output contract (SA-OUT-02/03):
- one bundle merges ESPN anchor + Browserbase noisy,
- collection is query-aware (different markets -> different sports/bundles),
- output is deterministic and de-duplicated.
"""

from pathlib import Path

import pytest

from app.schemas.market import Market
from app.services.espn.client import ESPNClient
from app.services.browserbase_service import BrowserbaseService
from app.services.sports_collector import collect_sports_evidence, derive_entities

ESPN_FIX = Path(__file__).parent / "fixtures" / "espn"
NOISY_FIX = Path(__file__).parent / "fixtures" / "noisy"
FIXED_TS = "2026-06-20T00:00:00Z"


@pytest.fixture(autouse=True)
def _search_offline(monkeypatch):
    """Keep the web-search discovery layer off the network in these tests."""
    monkeypatch.setenv("SEARCH_OFFLINE", "1")


def _espn():
    return ESPNClient(fixtures_dir=ESPN_FIX, offline=True)


def _bb(tmp_path):
    return BrowserbaseService(cache_dir=tmp_path, fixtures_dir=NOISY_FIX, offline=True)


def _market(sport_text):
    return Market(
        market_id="t", title=sport_text, question=sport_text,
        category="sports", resolution_criteria="n/a",
    )


@pytest.mark.parametrize("sport", ["soccer", "baseball"])
def test_bundle_merges_anchor_and_noisy(sport, tmp_path):
    chunks = collect_sports_evidence(
        _market(sport), sport=sport, observed_at=FIXED_TS,
        espn_client=_espn(), browserbase=_bb(tmp_path),
    )
    vias = {c.metadata["fetched_via"] for c in chunks}
    assert "http" in vias, f"{sport}: missing anchor (http) chunks"
    assert "browserbase" in vias, f"{sport}: missing noisy (browserbase) chunks"
    # all are sports_video, all carry the 4 standard metadata keys
    for c in chunks:
        assert c.source_type == "sports_video"
        assert {"kind", "fetched_via", "source_strength", "observed_at"} <= set(c.metadata)


@pytest.mark.parametrize("sport", ["soccer", "baseball"])
def test_anchor_only_and_noisy_only_toggles(sport, tmp_path):
    anchor_only = collect_sports_evidence(
        _market(sport), sport=sport, observed_at=FIXED_TS,
        espn_client=_espn(), browserbase=_bb(tmp_path), noisy=False,
    )
    assert anchor_only and all(c.metadata["fetched_via"] == "http" for c in anchor_only)

    noisy_only = collect_sports_evidence(
        _market(sport), sport=sport, observed_at=FIXED_TS,
        espn_client=_espn(), browserbase=_bb(tmp_path), anchor=False,
    )
    assert noisy_only and all(c.metadata["fetched_via"] == "browserbase" for c in noisy_only)


def test_deterministic(tmp_path):
    a = collect_sports_evidence(_market("soccer"), sport="soccer", observed_at=FIXED_TS,
                               espn_client=_espn(), browserbase=_bb(tmp_path))
    b = collect_sports_evidence(_market("soccer"), sport="soccer", observed_at=FIXED_TS,
                               espn_client=_espn(), browserbase=_bb(tmp_path))
    assert [(c.metadata["kind"], c.text) for c in a] == [(c.metadata["kind"], c.text) for c in b]


def test_query_aware_resolves_different_sports(tmp_path):
    """Different market questions -> different sports -> different bundles (SA-OUT-02)."""
    soccer = collect_sports_evidence(
        _market("Will Argentina win the FIFA World Cup soccer match?"),
        observed_at=FIXED_TS, espn_client=_espn(), browserbase=_bb(tmp_path),
    )
    mlb = collect_sports_evidence(
        _market("Will the Yankees win this MLB baseball game?"),
        observed_at=FIXED_TS, espn_client=_espn(), browserbase=_bb(tmp_path),
    )
    assert {c.metadata["sport"] for c in soccer} == {"soccer"}
    assert {c.metadata["sport"] for c in mlb} == {"baseball"}


def test_returns_list_of_evidence_chunks(tmp_path):
    from app.schemas.evidence import EvidenceChunk
    chunks = collect_sports_evidence(_market("soccer"), sport="soccer",
                                     espn_client=_espn(), browserbase=_bb(tmp_path))
    assert isinstance(chunks, list)
    assert all(isinstance(c, EvidenceChunk) for c in chunks)


# ---------------------------------------------------------------------------
# Entity derivation (SA-OUT-02)
# ---------------------------------------------------------------------------

def test_derive_entities_extracts_teams_and_thresholds():
    m = Market(
        market_id="x", title="Yankees vs Red Sox",
        question="Will the Yankees score over 4.5 runs against the Red Sox?",
        category="sports", resolution_criteria="n/a",
        protected_terms=["Yankees", "Red Sox"],
    )
    ent = derive_entities(m)
    assert "Yankees" in ent["entities"]
    assert "Red Sox" in ent["entities"]
    assert "4.5" in ent["thresholds"]
    # stopwords like "Will"/"The" are not surfaced as entities
    assert "Will" not in ent["entities"]
