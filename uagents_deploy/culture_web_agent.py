"""
CultureWebAgent - Standalone uAgent for culture/entertainment evidence collection.

This agent can be deployed to Agentverse and will respond to evidence requests
by collecting culture/web-related information.

For MVP: Reads from local sample file
For Production: Would integrate with Browserbase for live web scraping
"""

import os
import sys
import urllib.parse
from uagents import Agent, Context, Protocol
from protocols.messages import (
    EvidenceRequest,
    EvidenceResponse,
    EvidenceChunkMsg,
    AgentStatus
)

# Agent configuration
AGENT_NAME = "culture_web_agent"
AGENT_SEED = "culture_web_agent_seed_phrase_change_in_production"
AGENT_PORT = 8001
AGENT_MAILBOX = True  # Enable for Agentverse deployment

# Create the agent
agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

# Create protocol for evidence collection
evidence_protocol = Protocol("EvidenceCollection")


def _extract_search_terms(market_question: str) -> str:
    """Strip stop words and return up to 6 key terms for search queries."""
    stop = {
        'will', 'the', 'a', 'an', 'is', 'are', 'be', 'in', 'at', 'to', 'for',
        'of', 'and', 'or', 'on', 'by', 'with', 'this', 'that', 'have', 'has',
        'do', 'does', 'did', 'it', 'its', 'any', 'win', 'lose', 'get', 'make',
        'which', 'who', 'what', 'when', 'where', 'how', 'if', 'than', 'more',
    }
    words = [w.strip('?.,!') for w in market_question.lower().split()]
    return ' '.join([w for w in words if w.isalpha() and w not in stop and len(w) > 2][:6])


def _fetch_google_news_rss(market_question: str) -> list:
    """Fetch Google News RSS and return a list of (title, pub_date, source) tuples."""
    try:
        import httpx
        import xml.etree.ElementTree as ET
        terms = _extract_search_terms(market_question)
        encoded = urllib.parse.quote(terms)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SignalForge/1.0)"},
            timeout=12,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall('.//item')[:40]:
            title = item.findtext('title', '').strip()
            pub = item.findtext('pubDate', '').strip()
            source = (item.find('source') or None)
            source_name = source.text if source is not None else ''
            if title:
                text = f"{title}" + (f" — {source_name}" if source_name else "") + (f" ({pub[:16]})" if pub else "")
                items.append((text, url))
        return items
    except Exception:
        return []


def collect_culture_evidence(market_question: str, protected_terms: list) -> list:
    """Collect culture/entertainment evidence: Google News RSS primary, Browserbase secondary, static fallback."""
    evidence_chunks = []

    # -- Primary: Google News RSS (works from any IP, no browser needed) ------
    try:
        news_items = _fetch_google_news_rss(market_question)
        for text, source_url in news_items:
            evidence_chunks.append(EvidenceChunkMsg(
                source_type="culture_web",
                text=text,
                source_url=source_url,
                confidence=0.75,
                metadata={"agent": AGENT_NAME, "is_sample_data": False, "source": "google_news_rss"},
            ))
        if evidence_chunks:
            print(f"[{AGENT_NAME}] Fetched {len(evidence_chunks)} live headlines from Google News RSS")
    except Exception as exc:
        print(f"[{AGENT_NAME}] Google News RSS failed ({exc})")

    # -- Secondary: Browserbase browser for JS-heavy sources ------------------
    if len(evidence_chunks) < 10:
        try:
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            from dotenv import load_dotenv
            load_dotenv(os.path.join(_project_root, '.env'))
            if _project_root not in sys.path:
                sys.path.insert(0, _project_root)
            from app.services.browserbase_service import BrowserbaseService
            bb = BrowserbaseService()
            if bb.has_live_capability:
                terms = _extract_search_terms(market_question)
                encoded = urllib.parse.quote(terms)
                bb_url = f"https://www.bing.com/news/search?q={encoded}&format=rss"
                raw = bb.scrape_text(bb_url)
                if raw:
                    lines = [ln.strip() for ln in raw.split('\n') if ln.strip() and len(ln.split()) >= 8]
                    for line in lines[:20]:
                        evidence_chunks.append(EvidenceChunkMsg(
                            source_type="culture_web",
                            text=line,
                            source_url=bb_url,
                            confidence=0.65,
                            metadata={"agent": AGENT_NAME, "is_sample_data": False, "source": "browserbase_live"},
                        ))
                    print(f"[{AGENT_NAME}] Added {len(lines[:20])} Browserbase chunks")
        except Exception as exc:
            print(f"[{AGENT_NAME}] Browserbase secondary pass skipped ({exc})")

    # -- Fallback: static sample file -----------------------------------------
    if not evidence_chunks:
        sample_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "examples", "raw_context", "culture_web_context.txt",
        )
        if os.path.exists(sample_file_path):
            with open(sample_file_path, 'r') as f:
                raw_text = f.read()
            for para in [p.strip() for p in raw_text.split('\n\n') if p.strip()]:
                if len(para.split()) < 10:
                    continue
                evidence_chunks.append(EvidenceChunkMsg(
                    source_type="culture_web",
                    text=para,
                    source_url="local://examples/raw_context/culture_web_context.txt",
                    confidence=0.8,
                    metadata={"agent": AGENT_NAME, "is_sample_data": True},
                ))
        print(f"[{AGENT_NAME}] Using static file fallback: {len(evidence_chunks)} chunks")

    return evidence_chunks[:50]


@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    """
    Handle incoming evidence collection requests.

    Args:
        ctx: Agent context
        sender: Address of requesting agent
        msg: Evidence request message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received evidence request from {sender}")
    ctx.logger.info(f"Market question: {msg.market_question}")

    # Send status update
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Collecting culture/web evidence for: {msg.market_question}"
    ))

    # Collect evidence
    evidence_chunks = collect_culture_evidence(
        market_question=msg.market_question,
        protected_terms=msg.protected_terms
    )

    ctx.logger.info(f"[{AGENT_NAME}] Collected {len(evidence_chunks)} evidence chunks")

    try:
        from redis_service import append_claims
        market_id = msg.market_id or "UNKNOWN"
        append_claims(market_id, [c.model_dump() for c in evidence_chunks])
        ctx.logger.info(f"[{AGENT_NAME}] Wrote {len(evidence_chunks)} claims to Redis")
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Redis write skipped: {e}")

    try:
        from agent_memory_service import store_evidence
        market_id = msg.market_id or "UNKNOWN"
        for chunk in evidence_chunks:
            store_evidence(market_id, AGENT_NAME, chunk.text)
        ctx.logger.info(f"[{AGENT_NAME}] Stored {len(evidence_chunks)} events in Agent Memory")
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Agent Memory write skipped: {e}")

    # Send response
    response = EvidenceResponse(
        request_id=msg.msg_id,
        agent_name=AGENT_NAME,
        evidence_chunks=evidence_chunks,
        total_chunks=len(evidence_chunks)
    )

    await ctx.send(sender, response)

    # Send completion status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Sent {len(evidence_chunks)} evidence chunks"
    ))


# Include the protocol with the agent
agent.include(evidence_protocol)


# Startup message
@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to collect culture/web evidence")


if __name__ == "__main__":
    agent.run()
