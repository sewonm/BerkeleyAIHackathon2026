"""
CultureWebAgent — Fully self-contained uAgent for Agentverse deployment.

Searches the web for culture/entertainment evidence using Browserbase and
returns EvidenceChunks to the orchestrator. No external app/ imports.

Required secrets (set in Agentverse dashboard or local .env):
    BROWSERBASE_API_KEY   — Browserbase API key (enables fetch_api)
    SERPER_API_KEY        — Serper.dev key for web search (preferred)

Optional:
    CULTURE_AGENT_SEED    — deterministic seed for consistent agent address
"""

import os
import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Literal
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field
from uagents import Agent, Context, Protocol

# ---------------------------------------------------------------------------
# Inlined message models (no protocols/ folder needed on Agentverse)
# ---------------------------------------------------------------------------

class EvidenceRequest(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    market_question: str
    market_id: Optional[str] = None
    category: str
    protected_terms: List[str] = Field(default_factory=list)


class EvidenceChunkMsg(BaseModel):
    source_type: Literal[
        "culture_web", "sports_video", "politics_news",
        "financial_research", "market", "manual"
    ]
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: dict = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    agent_name: str
    evidence_chunks: List[EvidenceChunkMsg]
    total_chunks: int


class AgentStatus(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    status: Literal["ready", "processing", "completed", "error"]
    message: str

# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------

AGENT_NAME = "culture_web_agent"
AGENT_SEED = os.getenv("CULTURE_AGENT_SEED", "culture_web_agent_seed_change_in_production")
AGENT_PORT = 8001

agent = Agent(name=AGENT_NAME, seed=AGENT_SEED, port=AGENT_PORT, mailbox=True)
evidence_protocol = Protocol("EvidenceCollection")

# ---------------------------------------------------------------------------
# Browserbase / web search (inlined — no app/ imports needed)
# ---------------------------------------------------------------------------

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

BB_API_BASE = "https://api.browserbase.com/v1"


async def _bb_fetch(url: str) -> str:
    """Call Browserbase REST API directly — no SDK package needed."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{BB_API_BASE}/fetch",
            headers={"X-BB-API-Key": BROWSERBASE_API_KEY, "Content-Type": "application/json"},
            json={"url": url, "format": "markdown"},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("content") or data.get("text") or ""


async def _serper_search(query: str, max_results: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
        )
        r.raise_for_status()
        data = r.json()
    return [
        {"url": item.get("link", ""), "title": item.get("title", ""), "snippet": item.get("snippet", "")}
        for item in data.get("organic", [])[:max_results]
    ]


async def _bb_ddg_search(query: str, max_results: int) -> list[dict]:
    """Fetch DuckDuckGo HTML results via Browserbase — no bot blocking."""
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    try:
        content = await _bb_fetch(search_url)
    except Exception:
        return []
    # Exclude DuckDuckGo's own domain from results
    links = re.findall(r'\[([^\]]+)\]\((https?://(?!(?:www\.)?duckduckgo\.)[^\)]+)\)', content)
    return [{"url": url, "title": title, "snippet": ""} for title, url in links[:max_results]]


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    if SERPER_API_KEY:
        try:
            return await _serper_search(query, max_results)
        except Exception as e:
            print(f"[culture_web_agent] Serper failed: {e}")
    if BROWSERBASE_API_KEY:
        try:
            return await _bb_ddg_search(query, max_results)
        except Exception as e:
            print(f"[culture_web_agent] BB search failed: {e}")
    print(f"[culture_web_agent] WARNING: falling back to mock. BB key set={bool(BROWSERBASE_API_KEY)}")
    return [{"url": "https://example.com/mock", "title": f"Mock: {query}", "snippet": f"Mock result for: {query}"}]


async def fetch_as_markdown(url: str) -> str:
    if BROWSERBASE_API_KEY:
        try:
            return await _bb_fetch(url)
        except Exception:
            pass
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text[:5000]
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------

_QUERY_TEMPLATES = [
    "{q}",
    "{q} latest news",
    "{q} entertainment odds prediction",
]

_HAVE_LIVE_SEARCH = bool(SERPER_API_KEY or BROWSERBASE_API_KEY)


async def collect_culture_evidence(market_question: str, protected_terms: list[str]) -> list[EvidenceChunkMsg]:
    now = datetime.now(timezone.utc).isoformat()
    chunks = []

    for template in _QUERY_TEMPLATES[:3]:
        query = template.format(q=market_question)
        try:
            results = await search_web(query, max_results=2)
        except Exception:
            results = []

        for hit in results:
            url = hit.get("url", "")
            title = hit.get("title", "")
            snippet = hit.get("snippet", "")

            content = snippet
            if _HAVE_LIVE_SEARCH and url and not url.startswith("https://example.com"):
                try:
                    fetched = await fetch_as_markdown(url)
                    if fetched.strip():
                        content = fetched[:2000]
                except Exception:
                    pass

            if not content.strip():
                continue

            chunks.append(EvidenceChunkMsg(
                source_type="culture_web",
                text=(
                    f"=== Culture/Web Source: {title} ===\n"
                    f"URL: {url}\n"
                    f"Query: {query}\n\n"
                    f"{content}"
                ),
                source_url=url,
                timestamp=now,
                confidence=0.8 if _HAVE_LIVE_SEARCH else 0.0,
                metadata={"query": query, "title": title, "mock": not _HAVE_LIVE_SEARCH},
            ))

    return chunks

# ---------------------------------------------------------------------------
# uAgent message handler
# ---------------------------------------------------------------------------

@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    ctx.logger.info(f"[{AGENT_NAME}] Request from {sender} — {msg.market_question}")

    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Searching web for: {msg.market_question}",
    ))

    try:
        chunks = await collect_culture_evidence(msg.market_question, msg.protected_terms)
    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Error: {e}")
        await ctx.send(sender, AgentStatus(agent_name=AGENT_NAME, status="error", message=str(e)))
        return

    ctx.logger.info(f"[{AGENT_NAME}] Collected {len(chunks)} chunks | mock={chunks[0].metadata.get('mock') if chunks else 'N/A'}")
    for i, chunk in enumerate(chunks[:2]):
        preview = chunk.text[:300].replace("\n", " ")
        ctx.logger.info(f"[{AGENT_NAME}] Chunk {i+1}: {preview}")

    await ctx.send(sender, EvidenceResponse(
        request_id=msg.msg_id,
        agent_name=AGENT_NAME,
        evidence_chunks=chunks,
        total_chunks=len(chunks),
    ))

    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Sent {len(chunks)} culture/web evidence chunks",
    ))


agent.include(evidence_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] address: {agent.address}")
    ctx.logger.info(f"Browserbase: {'LIVE (len=' + str(len(BROWSERBASE_API_KEY)) + ')' if BROWSERBASE_API_KEY else 'NOT SET — check secret name'}")
    ctx.logger.info(f"Serper:      {'LIVE' if SERPER_API_KEY else 'NOT SET'}")


if __name__ == "__main__":
    agent.run()
