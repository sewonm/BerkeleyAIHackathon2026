"""
Web-search discovery layer tests (offline, deterministic).

Parsers are tested against small captured-shape samples; query building +
collection are tested without touching the network.
"""

import pytest

from app.schemas.market import Market
from app.services.espn.registry import resolve_sport, get_sport_config
from app.services.web_search import (
    WebSearchService,
    SearchResult,
    build_search_queries,
    collect_search_evidence,
)

GOOGLE_NEWS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Messi injury update before World Cup - ESPN</title>
    <link>https://news.google.com/rss/articles/ABC123</link>
    <description>&lt;a href="x"&gt;Messi injury update before World Cup&lt;/a&gt; ESPN</description>
    <source url="https://espn.com">ESPN</source>
  </item>
  <item>
    <title>Argentina squad news - Reuters</title>
    <link>https://news.google.com/rss/articles/DEF456</link>
    <description>Argentina squad news Reuters</description>
    <source url="https://reuters.com">Reuters</source>
  </item>
</channel></rss>"""

DDG_SAMPLE = """
<div><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.espn.com%2Fsoccer%2Fstory%2Fid%2F1&amp;rut=abc">World Cup injuries tracker</a></div>
<a class="result__snippet">Here is the latest on key injuries impacting World Cup teams.</a>
<div><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Flatination.com%2Fargentina&amp;rut=def">Argentina on high alert</a></div>
<a class="result__snippet">Argentina faces critical injuries days before its debut.</a>
"""

ESPN_NEWS_SAMPLE = """{"articles":[
  {"headline":"World Cup Daily: Dutch win big","description":"Another weekend of action.",
   "links":{"web":{"href":"https://www.espn.com/soccer/story/_/id/1"}}},
  {"headline":"Coach slams lack of fair play","description":"Criticism after the match.",
   "links":{"web":{"href":"https://www.espn.com/soccer/story/_/id/2"}}}
]}"""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def test_parse_google_news():
    res = WebSearchService._parse_google_news(GOOGLE_NEWS_SAMPLE, "q")
    assert len(res) == 2
    assert res[0].title.startswith("Messi injury update")
    assert res[0].source == "ESPN"
    assert res[0].provider == "google_news"
    assert "<a" not in res[0].snippet  # html stripped


def test_parse_ddg_decodes_real_url():
    res = WebSearchService._parse_ddg(DDG_SAMPLE, "q")
    assert len(res) == 2
    assert res[0].url == "https://www.espn.com/soccer/story/id/1"  # uddg decoded
    assert "injuries" in res[0].snippet.lower()
    assert res[0].provider == "duckduckgo"


def test_parse_espn_news():
    res = WebSearchService._parse_espn_news(ESPN_NEWS_SAMPLE, "soccer/fifa.world")
    assert len(res) == 2
    assert res[0].url.endswith("/id/1")
    assert res[0].source == "ESPN"


def test_parsers_never_raise_on_garbage():
    assert WebSearchService._parse_google_news("not xml", "q") == []
    assert WebSearchService._parse_espn_news("not json", "q") == []
    assert WebSearchService._parse_ddg("", "q") == []


# ---------------------------------------------------------------------------
# Query building (query-aware)
# ---------------------------------------------------------------------------

def test_build_queries_uses_entities_and_intents():
    m = Market(market_id="x", title="Argentina World Cup",
               question="Will Argentina win the 2026 FIFA World Cup?",
               category="sports", resolution_criteria="r",
               protected_terms=["Argentina"])
    qs = build_search_queries(m, resolve_sport(m), max_queries=6)
    assert qs[0].startswith("Will Argentina")     # raw question first
    assert any("Argentina" in q and "injury" in q for q in qs)
    assert any("odds" in q for q in qs)
    assert len(qs) <= 6


def test_different_markets_give_different_queries():
    m1 = Market(market_id="1", title="Yankees", question="Will the Yankees win? MLB baseball",
                category="sports", resolution_criteria="r", protected_terms=["Yankees"])
    m2 = Market(market_id="2", title="Lakers", question="Will the Lakers win? NBA basketball",
                category="sports", resolution_criteria="r", protected_terms=["Lakers"])
    assert build_search_queries(m1, resolve_sport(m1)) != build_search_queries(m2, resolve_sport(m2))


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class _FakeWeb:
    """Returns canned results regardless of query/provider."""
    def google_news(self, q, limit=None):
        return [SearchResult(f"GN {q} A", "https://a.com/1", "snip", "SrcA", "google_news", q),
                SearchResult(f"GN {q} B", "https://b.com/2", "snip", "SrcB", "google_news", q)]
    def duckduckgo(self, q, limit=None):
        return [SearchResult(f"DDG {q}", "https://a.com/1", "snip", "a.com", "duckduckgo", q)]  # dup url
    def espn_news(self, sport, league, limit=None):
        return [SearchResult("ESPN art", "https://espn.com/x", "d", "ESPN", "espn_news", "espn")]


def test_collect_search_evidence_dedupes_and_normalizes():
    m = Market(market_id="x", title="Argentina World Cup",
               question="Will Argentina win the World Cup?", category="sports",
               resolution_criteria="r", protected_terms=["Argentina"])
    cfg = resolve_sport(m)
    chunks = collect_search_evidence(m, sport_cfg=cfg, observed_at="2026-06-20T00:00:00Z",
                                     web=_FakeWeb(), max_queries=2)
    assert chunks, "expected discovery chunks"
    for c in chunks:
        assert c.source_type == "sports_video"
        assert c.metadata["fetched_via"] == "search"
        assert c.metadata["source_strength"] == "noisy"
        assert c.metadata["sport"] == cfg.key
    # dedupe by url: https://a.com/1 appears in GN + DDG -> once
    urls = [c.source_url for c in chunks]
    assert urls.count("https://a.com/1") == 1


def test_collect_search_offline_no_fixtures_is_empty():
    m = Market(market_id="x", title="soccer", question="soccer world cup",
               category="sports", resolution_criteria="r")
    web = WebSearchService(offline=True)  # no fixtures -> nothing
    assert collect_search_evidence(m, sport="soccer", web=web) == []
