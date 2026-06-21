"""
Phase 3 — noisy collector tests (deterministic, offline, fixture-backed).

Verifies the noisy layer returns raw-text EvidenceChunks from >= 2 sources per
sport (SA-SCRAPE-02/03), normalized with the right metadata, deterministically.
"""

from pathlib import Path

import pytest

from app.schemas.market import Market
from app.services.browserbase_service import BrowserbaseService
from app.services.noisy_collector import collect_noisy_evidence

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "noisy"
FIXED_TS = "2026-06-20T00:00:00Z"
SPORTS = ["soccer", "baseball"]

REQUIRED_METADATA = {
    "kind", "fetched_via", "sport", "source_strength", "observed_at", "label",
}


def _service(tmp_path) -> BrowserbaseService:
    # cache empty (tmp) -> falls through to shipped fixtures, hard offline.
    return BrowserbaseService(
        cache_dir=tmp_path, fixtures_dir=FIXTURES_DIR, offline=True
    )


def _collect(sport, tmp_path):
    market = Market(
        market_id=f"t-{sport}", title=sport, question=sport,
        category="sports", resolution_criteria="n/a",
    )
    return collect_noisy_evidence(
        market, service=_service(tmp_path), sport=sport, observed_at=FIXED_TS
    )


@pytest.mark.parametrize("sport", SPORTS)
class TestNoisyCollection:

    def test_two_or_more_sources(self, sport, tmp_path):
        chunks = _collect(sport, tmp_path)
        assert len(chunks) >= 2, f"{sport}: need >= 2 noisy sources, got {len(chunks)}"

    def test_distinct_sources(self, sport, tmp_path):
        chunks = _collect(sport, tmp_path)
        urls = {c.source_url for c in chunks}
        assert len(urls) >= 2  # SA-SCRAPE-02/03: >= 2 distinct noisy sources

    def test_metadata_contract(self, sport, tmp_path):
        for c in _collect(sport, tmp_path):
            assert c.source_type == "sports_video"
            missing = REQUIRED_METADATA - set(c.metadata)
            assert not missing, f"missing {missing}"
            assert c.metadata["fetched_via"] == "browserbase"
            assert c.metadata["source_strength"] == "noisy"
            assert c.metadata["sport"] == sport

    def test_raw_text_present(self, sport, tmp_path):
        for c in _collect(sport, tmp_path):
            assert c.text and len(c.text) > 20

    def test_deterministic(self, sport, tmp_path):
        a = _collect(sport, tmp_path)
        b = _collect(sport, tmp_path)
        assert [(c.metadata["kind"], c.text) for c in a] == \
               [(c.metadata["kind"], c.text) for c in b]


def test_empty_when_no_data(tmp_path):
    """No cache + no fixtures + offline -> empty, never raises."""
    svc = BrowserbaseService(cache_dir=tmp_path, offline=True)
    market = Market(
        market_id="x", title="soccer", question="soccer",
        category="sports", resolution_criteria="n/a",
    )
    assert collect_noisy_evidence(market, service=svc, sport="soccer") == []


def test_max_targets_caps(tmp_path):
    market = Market(
        market_id="x", title="soccer", question="soccer",
        category="sports", resolution_criteria="n/a",
    )
    chunks = collect_noisy_evidence(
        market, service=_service(tmp_path), sport="soccer",
        observed_at=FIXED_TS, max_targets=1,
    )
    assert len(chunks) <= 1
