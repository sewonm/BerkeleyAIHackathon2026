"""
Evidence-bundle logic for the deployed culture/web uAgent.

Kept separate from culture_web_agent.py (mirrors sports_evidence.py) so the bundle
building is importable and unit-testable WITHOUT constructing a uAgent / touching
the Agentverse network. The deployed agent imports collect_bundle /
format_chat_reply / build_stub_bundle from here.

LIVE DATA: this agent is fully self-contained (no app.services.* imports), so it
deploys equally well as a hosted Agentverse agent OR a local mailbox agent. The web
layer is built from two providers, tried in order:
  * Serper.dev  (preferred) — Google search results as clean JSON.
  * Browserbase — DuckDuckGo HTML rendered through a real browser (no bot blocking),
    plus per-URL page fetch as markdown.
If neither key is set / both fail, it degrades to a tiny canned stub bundle so a
reply is NEVER empty (demo-safety, same contract as the sports agent).
"""

from __future__ import annotations

import os
import re
import json
import asyncio
import urllib.parse
from datetime import datetime, timezone

import httpx

from protocols.messages import EvidenceChunkMsg

# ---------------------------------------------------------------------------
# Provider keys + capability flag (read once at import; set as Agentverse secrets)
# ---------------------------------------------------------------------------

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

BB_API_BASE = "https://api.browserbase.com/v1"

# Mirrors sports_evidence.LIVE_AVAILABLE: True when a real web layer is reachable.
LIVE_AVAILABLE = bool(SERPER_API_KEY or BROWSERBASE_API_KEY)
IMPORT_ERR = None if LIVE_AVAILABLE else "no SERPER_API_KEY or BROWSERBASE_API_KEY set"

# Query intents fanned out around the market question (entity-agnostic so it works
# for awards / box office / streaming / celebrity / music-chart markets alike).
_QUERY_TEMPLATES = [
    ("{q}", "news"),
    ("{q} latest news", "news"),
    ("{q} prediction odds", "odds"),
]


# ---------------------------------------------------------------------------
# Web providers (async; httpx) — inlined, no SDK packages required
# ---------------------------------------------------------------------------

async def _bb_fetch(url: str) -> str:
    """Render a URL through Browserbase and return its content as markdown."""
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.post(
            f"{BB_API_BASE}/fetch",
            headers={"X-BB-API-Key": os.getenv("BROWSERBASE_API_KEY") or BROWSERBASE_API_KEY, "Content-Type": "application/json"},
            json={"url": url, "format": "markdown"},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("content") or data.get("text") or ""


async def _serper_search(query: str, max_results: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": os.getenv("SERPER_API_KEY") or SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
        )
        r.raise_for_status()
        data = r.json()
    return [
        {"url": item.get("link", ""), "title": item.get("title", ""), "snippet": item.get("snippet", ""),
         "provider": "serper"}
        for item in data.get("organic", [])[:max_results]
    ]


_IMAGE_EXTS = ('.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')

async def _bb_ddg_search(query: str, max_results: int) -> list[dict]:
    """Fetch DuckDuckGo HTML results via Browserbase — no bot blocking."""
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    try:
        content = await _bb_fetch(search_url)
    except Exception:
        return []
    all_links = re.findall(r'\[([^\]]*)\]\((https?://[^\)]+)\)', content)
    results = []
    for title, url in all_links:
        # Skip favicon/image links and DDG icon proxy
        if title.strip().startswith('!') or 'external-content.duckduckgo.com' in url:
            continue
        if any(url.lower().endswith(ext) for ext in _IMAGE_EXTS):
            continue
        # Decode DDG redirect links (/l/?uddg=...)
        if '/l/?' in url and 'uddg=' in url:
            m = re.search(r'uddg=([^&]+)', url)
            if m:
                url = urllib.parse.unquote(m.group(1))
            else:
                continue
        # Skip remaining DDG internal links
        if 'duckduckgo.com' in url:
            continue
        results.append({"url": url, "title": title.strip(), "snippet": "", "provider": "browserbase"})
        if len(results) >= max_results:
            break
    return results


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Serper first, Browserbase/DDG second. Returns [] if no provider succeeds."""
    serper_key = os.getenv("SERPER_API_KEY") or SERPER_API_KEY
    bb_key = os.getenv("BROWSERBASE_API_KEY") or BROWSERBASE_API_KEY
    if serper_key:
        try:
            return await _serper_search(query, max_results)
        except Exception as e:
            print(f"[culture_web_agent] Serper failed: {e}")
    if bb_key:
        try:
            return await _bb_ddg_search(query, max_results)
        except Exception as e:
            print(f"[culture_web_agent] Browserbase search failed: {e}")
    return []


async def fetch_as_markdown(url: str) -> str:
    """Best-effort page body: Browserbase render first, then a plain httpx GET."""
    if BROWSERBASE_API_KEY:
        try:
            return await _bb_fetch(url)
        except Exception:
            pass
    try:
        async with httpx.AsyncClient(timeout=4, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text[:5000]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Bundle building (mirrors sports_evidence.collect_bundle / build_stub_bundle)
# ---------------------------------------------------------------------------

def build_stub_bundle(market_question: str) -> list:
    """Tiny canned bundle — last-resort fallback so a reply is never empty."""
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = (market_question or "")[:60]
    return [
        EvidenceChunkMsg(
            source_type="culture_web",
            text=f"(stub) No live web provider configured — re: {preview}",
            source_url="stub://culture/fallback",
            confidence=0.5,
            metadata={"kind": "news", "fetched_via": "stub",
                      "source_strength": "stub", "observed_at": observed_at},
        ),
        EvidenceChunkMsg(
            source_type="culture_web",
            text="(stub) Set SERPER_API_KEY or BROWSERBASE_API_KEY as an Agentverse "
                 "secret to enable live culture/entertainment web evidence.",
            source_url="stub://culture/fallback",
            confidence=0.5,
            metadata={"kind": "news", "fetched_via": "stub",
                      "source_strength": "stub", "observed_at": observed_at},
        ),
    ]


async def collect_bundle(question: str, category: str = "culture", protected_terms: list | None = None):
    """Build the culture/web evidence bundle for a market question. ASYNC (awaits httpx).

    Returns ``(list[EvidenceChunkMsg], meta)``. Demo-safe ladder:
    live (Serper/Browserbase) -> stub. Never raises.
    """
    # Re-check at call time in case keys were loaded after module import (e.g. dotenv in bridge)
    live = bool(os.getenv("SERPER_API_KEY") or os.getenv("BROWSERBASE_API_KEY"))
    if not live:
        return build_stub_bundle(question), {"source": "stub", "providers": [], "queries": 0}

    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = datetime.now(timezone.utc).isoformat()
    chunks: list[EvidenceChunkMsg] = []
    providers: set[str] = set()
    seen_urls: set[str] = set()

    # Run all search queries concurrently.
    async def _search_one(template, kind):
        query = template.format(q=question or "")
        try:
            results = await asyncio.wait_for(search_web(query, max_results=2), timeout=5.0)
        except Exception:
            results = []
        return query, kind, results

    search_tasks = [_search_one(t, k) for t, k in _QUERY_TEMPLATES]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Collect all hits, dedup by URL.
    pending: list[tuple[str, str, str, str, str]] = []  # (url, title, snippet, provider, query, kind)
    for item in search_results:
        if isinstance(item, Exception):
            continue
        query, kind, results = item
        for hit in results:
            url = hit.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            pending.append((url, hit.get("title", ""), hit.get("snippet", ""), hit.get("provider", "web"), query, kind))

    # Fetch all pages concurrently with a tight 3s timeout per URL.
    async def _fetch_one(url, title, snippet, provider, query, kind):
        content = snippet
        if url and not url.startswith("stub://"):
            try:
                fetched = await asyncio.wait_for(fetch_as_markdown(url), timeout=3.0)
                if fetched.strip():
                    content = fetched[:2000]
            except Exception:
                pass
        return url, title, content, provider, query, kind

    fetch_tasks = [_fetch_one(*p) for p in pending]
    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    for item in fetch_results:
        if isinstance(item, Exception):
            continue
        url, title, content, provider, query, kind = item
        if not content.strip():
            continue
        providers.add(provider)
        chunks.append(EvidenceChunkMsg(
            source_type="culture_web",
            text=(
                f"=== Culture/Web Source: {title} ===\n"
                f"URL: {url}\nQuery: {query}\n\n{content}"
            ),
            source_url=url,
            timestamp=now_iso,
            confidence=0.8,
            metadata={"kind": kind, "fetched_via": provider, "source_strength": "web",
                      "observed_at": observed_at, "query": query, "title": title},
        ))

    if len(chunks) < 2:  # nothing useful came back -> stub so a reply is never empty
        return build_stub_bundle(question), {"source": "stub", "providers": sorted(providers), "queries": len(_QUERY_TEMPLATES)}

    meta = {"source": "live", "providers": sorted(providers), "queries": len(_QUERY_TEMPLATES)}
    return chunks, meta


def collect_bundle_sync(question: str, category: str = "culture", protected_terms: list | None = None):
    """Blocking wrapper around collect_bundle for callers without an event loop."""
    return asyncio.run(collect_bundle(question, category, protected_terms))


# ---------------------------------------------------------------------------
# Chat reply formatter (mirrors sports_evidence.format_chat_reply)
# ---------------------------------------------------------------------------

def format_chat_reply(question: str, msgs: list, meta: dict) -> str:
    """Human-readable evidence summary for ASI:One + full JSON bundle for machines."""
    lines = [f'🎬 Culture/web evidence bundle for: "{(question or "").strip()[:140]}"']
    if meta.get("providers"):
        lines.append("Providers: " + ", ".join(meta["providers"]))
    lines.append(f"Source: {meta.get('source', 'live')} • {len(msgs)} chunks")

    SHOW = 14
    lines.append("")
    lines.append("Highlights:")
    for m in msgs[:SHOW]:
        title = m.metadata.get("title") or ((m.text or "").splitlines()[0] if m.text else "")
        lines.append(f"• [{m.metadata.get('kind', '?')}] {title[:100]}")
    if len(msgs) > SHOW:
        lines.append(f"…and {len(msgs) - SHOW} more (full bundle in JSON below)")

    lines.append("")
    lines.append("```json")
    lines.append(json.dumps([m.model_dump() for m in msgs], default=str))
    lines.append("```")
    return "\n".join(lines)