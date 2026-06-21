"""
General web-search discovery layer ("scour a lot more").

Turns a market into many search queries (entity x intent templates), hits keyless
search providers, and returns a wide set of raw result chunks — the broad discovery
fuel for the compression engine. Optionally deep-scrapes the top result URLs via
Browserbase for full article text.

Providers (all keyless, no API key):
  * Google News RSS  — query-driven headlines + snippets (up to ~100/query)
  * DuckDuckGo HTML  — general web results (title + snippet + real URL)
  * ESPN news        — per-league structured articles

Determinism/offline: WebSearchService supports fixtures + cache + offline, keyed by
provider+query, so tests are stable and the demo survives the network being off.
"""

from __future__ import annotations

import html
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode, urlparse, parse_qs, unquote

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""       # publisher
    provider: str = ""     # google_news | duckduckgo | espn_news
    query: str = ""


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def _key(provider: str, q: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", f"{provider}__{q}")
    return f"{safe[:180]}.txt"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class WebSearchService:
    """Keyless multi-provider search. Each fetch degrades gracefully (returns [])."""

    def __init__(
        self,
        *,
        cache_dir: Optional[str | Path] = None,
        fixtures_dir: Optional[str | Path] = None,
        offline: bool = False,
        timeout: float = 12.0,
        user_agent: str = DEFAULT_USER_AGENT,
        max_per_query: int = 10,
    ) -> None:
        cache_dir = cache_dir or os.getenv("SEARCH_CACHE_DIR") or None
        fixtures_dir = fixtures_dir or os.getenv("SEARCH_FIXTURES_DIR") or None
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None
        if not offline:
            offline = os.getenv("SEARCH_OFFLINE", "").strip().lower() in {"1", "true", "yes"}
        self.offline = offline
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_per_query = max_per_query
        if self.cache_dir:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    # -- raw text fetch (fixtures -> cache -> net) -------------------------

    def _fetch_text(self, key: str, url: str, params: Optional[dict] = None) -> Optional[str]:
        if self.fixtures_dir is not None:
            fx = self._read(self.fixtures_dir / key)
            if fx is not None:
                return fx
            if self.offline:
                return None
        if self.cache_dir is not None:
            c = self._read(self.cache_dir / key)
            if c is not None:
                return c
        if self.offline:
            return None
        text = self._http(url, params)
        if text and self.cache_dir is not None:
            self._write(self.cache_dir / key, text)
        return text

    def _http(self, url: str, params: Optional[dict]) -> Optional[str]:
        full = url + (("?" + urlencode(params)) if params else "")
        headers = {"User-Agent": self.user_agent}
        try:
            import httpx
            r = httpx.get(full, headers=headers, timeout=self.timeout, follow_redirects=True)
            return r.text if r.status_code == 200 else None
        except Exception:
            try:
                import urllib.request
                req = urllib.request.Request(full, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode("utf-8", "replace")
            except Exception:
                return None

    # -- providers ---------------------------------------------------------

    def google_news(self, query: str, limit: Optional[int] = None) -> List[SearchResult]:
        params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        text = self._fetch_text(_key("google_news", query),
                                "https://news.google.com/rss/search", params)
        return self._parse_google_news(text, query)[: (limit or self.max_per_query)] if text else []

    def duckduckgo(self, query: str, limit: Optional[int] = None) -> List[SearchResult]:
        text = self._fetch_text(_key("duckduckgo", query),
                                "https://html.duckduckgo.com/html/", {"q": query})
        return self._parse_ddg(text, query)[: (limit or self.max_per_query)] if text else []

    def espn_news(self, sport: str, league: str, limit: Optional[int] = None) -> List[SearchResult]:
        q = f"{sport}/{league}"
        text = self._fetch_text(_key("espn_news", q),
                                f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/news")
        return self._parse_espn_news(text, q)[: (limit or self.max_per_query)] if text else []

    # -- parsers (static -> unit-testable) --------------------------------

    @staticmethod
    def _parse_google_news(text: str, query: str) -> List[SearchResult]:
        out: List[SearchResult] = []
        try:
            root = ET.fromstring(text)
        except Exception:
            return out
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            desc = _strip_html(it.findtext("description") or "")
            src_el = it.find("source")
            source = (src_el.text or "").strip() if src_el is not None else ""
            if title:
                out.append(SearchResult(title=title, url=link, snippet=desc,
                                        source=source, provider="google_news", query=query))
        return out

    @staticmethod
    def _parse_ddg(text: str, query: str) -> List[SearchResult]:
        out: List[SearchResult] = []
        anchors = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S)
        snips = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', text, re.S)
        for i, (href, title_html) in enumerate(anchors):
            real = href
            try:
                if "uddg=" in href:
                    real = unquote(parse_qs(urlparse("https:" + href if href.startswith("//") else href).query)["uddg"][0])
            except Exception:
                pass
            snippet = _strip_html(snips[i]) if i < len(snips) else ""
            title = _strip_html(title_html)
            if title:
                out.append(SearchResult(title=title, url=real, snippet=snippet,
                                        source=urlparse(real).netloc, provider="duckduckgo", query=query))
        return out

    @staticmethod
    def _parse_espn_news(text: str, query: str) -> List[SearchResult]:
        out: List[SearchResult] = []
        try:
            data = json.loads(text)
        except Exception:
            return out
        for a in data.get("articles", []):
            web = ((a.get("links") or {}).get("web") or {}).get("href", "")
            title = (a.get("headline") or "").strip()
            if title:
                out.append(SearchResult(title=title, url=web,
                                        snippet=_strip_html(a.get("description", "")),
                                        source="ESPN", provider="espn_news", query=query))
        return out

    # -- io ---------------------------------------------------------------

    @staticmethod
    def _read(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding="utf-8") if path.is_file() else None
        except Exception:
            return None

    @staticmethod
    def _write(path: Path, text: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Query building (query-aware) + collection
# ---------------------------------------------------------------------------

INTENTS = ("injury report", "odds prediction", "lineup", "preview", "news")


def build_search_queries(market, sport_cfg, max_queries: int = 6) -> List[str]:
    """Build entity x intent search queries from the market (query-aware)."""
    from app.services.sports_collector import derive_entities  # lazy: avoid cycle

    ent = derive_entities(market)
    entities = ent["entities"][:3]
    sport_word = sport_cfg.display.split("(")[0].strip() if sport_cfg else ""

    queries: List[str] = []
    # the raw question is the strongest single query
    q = getattr(market, "question", None) or (market if isinstance(market, str) else "")
    if q:
        queries.append(q.strip())
    # entity x intent
    for e in entities:
        for intent in ("injury", "odds"):
            queries.append(f"{e} {sport_word} {intent}".strip())
    # matchup preview if we have two teams
    if len(entities) >= 2:
        queries.append(f"{entities[0]} vs {entities[1]} preview")

    # dedupe, cap
    seen, out = set(), []
    for x in queries:
        k = x.lower()
        if x and k not in seen:
            seen.add(k)
            out.append(x)
        if len(out) >= max_queries:
            break
    return out


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_search_evidence(
    market,
    *,
    sport_cfg=None,
    sport: Optional[str] = None,
    observed_at: Optional[str] = None,
    web: Optional[WebSearchService] = None,
    providers: tuple = ("google_news", "duckduckgo", "espn_news"),
    max_queries: int = 6,
    per_query: int = 8,
    max_results: int = 60,
    deep_scrape_top: int = 0,
    browserbase=None,
):
    """Discover wide raw evidence via web search. Returns list[EvidenceChunk].

    deep_scrape_top>0 fetches full text for the top-N result URLs via Browserbase
    (slower / uses sessions); default 0 = snippets only (fast, keyless).
    """
    from app.schemas.evidence import EvidenceChunk  # lazy: keep import graph light
    from app.services.espn.registry import resolve_sport, get_sport_config

    observed_at = observed_at or _utc_now()
    if sport_cfg is None:
        sport_cfg = get_sport_config(sport) if sport else resolve_sport(market)
    web = web or WebSearchService()

    queries = build_search_queries(market, sport_cfg, max_queries=max_queries)

    results: List[SearchResult] = []
    # ESPN news first (structured + high-quality), then per-query web results
    if "espn_news" in providers:
        results += web.espn_news(sport_cfg.espn_sport, sport_cfg.espn_league, limit=per_query)
    for q in queries:
        if "google_news" in providers:
            results += web.google_news(q, limit=per_query)
        if "duckduckgo" in providers:
            results += web.duckduckgo(q, limit=per_query)

    # dedupe by normalized url, then by title
    seen_url, seen_title, deduped = set(), set(), []
    for r in results:
        u = (r.url or "").split("?")[0].rstrip("/").lower()
        t = r.title.lower()
        if (u and u in seen_url) or t in seen_title:
            continue
        if u:
            seen_url.add(u)
        seen_title.add(t)
        deduped.append(r)
        if len(deduped) >= max_results:
            break

    chunks: List[EvidenceChunk] = []
    for r in deduped:
        text = r.title + (f" — {r.snippet}" if r.snippet else "")
        chunks.append(EvidenceChunk(
            source_type="sports_video",
            text=text,
            source_url=r.url or None,
            timestamp=observed_at,
            confidence=0.3,  # discovery snippet: lowest trust, widest net
            metadata={
                "kind": "news", "fetched_via": "search", "sport": sport_cfg.key,
                "source_strength": "noisy", "observed_at": observed_at,
                "provider": r.provider, "query": r.query, "publisher": r.source,
                "league": sport_cfg.espn_league,
            },
        ))

    # optional deep-scrape of the top URLs via Browserbase
    if deep_scrape_top and browserbase is not None:
        scraped = 0
        for r in deduped:
            if scraped >= deep_scrape_top:
                break
            if not r.url:
                continue
            try:
                full = browserbase.scrape_text(r.url)
            except Exception:
                full = None
            if full:
                chunks.append(EvidenceChunk(
                    source_type="sports_video",
                    text=f"{r.title}\n{full}",
                    source_url=r.url,
                    timestamp=observed_at,
                    confidence=0.45,
                    metadata={
                        "kind": "article", "fetched_via": "browserbase",
                        "sport": sport_cfg.key, "source_strength": "noisy",
                        "observed_at": observed_at, "provider": r.provider,
                        "publisher": r.source, "league": sport_cfg.espn_league,
                    },
                ))
                scraped += 1

    return chunks
