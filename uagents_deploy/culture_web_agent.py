"""
CultureWebAgent — Deployed Fetch.ai uAgent for culture/entertainment web evidence.

Address is derived from CULTURE_WEB_AGENT_SEED — keep this seed constant forever.
A fixed seed produces a byte-for-byte identical agent1q… address across every restart.

Dual-protocol agent (same shape as sports_video_agent.py):
  1. Chat Protocol v0.3.0 (ASI:One discoverable via publish_manifest=True)
     — receives a ChatMessage with a market question, ACKs immediately, then replies
       with a human-readable evidence summary + the full JSON bundle.
  2. Custom EvidenceCollection protocol (orchestrator_agent.py compat)
     — receives EvidenceRequest, returns EvidenceResponse with the same bundle.

LIVE DATA: fully self-contained (no app.services.* imports). The web layer
(Serper.dev + Browserbase/DuckDuckGo + httpx fallback) lives in culture_evidence.py.
The handler ACKs first, then awaits the async collection with a hard timeout. If no
web provider is configured / available, it degrades to a tiny stub bundle — the demo
NEVER returns nothing.

Required secrets (set in the Agentverse dashboard or local .env):
    SERPER_API_KEY        — Serper.dev key for Google search results (preferred)
    BROWSERBASE_API_KEY   — Browserbase key (DuckDuckGo HTML + page render fallback)
Optional:
    CULTURE_WEB_AGENT_SEED — deterministic seed for a stable agent address

DEPLOY AS A MAILBOX AGENT (mailbox=True): run this file locally
    python uagents_deploy/culture_web_agent.py
then open the Agent Inspector link printed in the terminal -> Connect -> Mailbox ->
Finish. That connects it to Agentverse and makes it discoverable on ASI:One.
"""

import os
import asyncio

# Load .env (repo root) so SERPER_API_KEY / BROWSERBASE_API_KEY / CULTURE_WEB_AGENT_SEED
# are available when the agent runs locally — must happen before any os.getenv below.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from uagents import Agent, Context, Protocol
from protocols.messages import (
    EvidenceRequest,
    EvidenceResponse,
)
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

# Bundle-building logic lives in culture_evidence.py (importable + unit-testable
# without constructing a uAgent). Self-contained web layer — no app/ imports.
from culture_evidence import (
    collect_bundle,
    build_stub_bundle,
    format_chat_reply,
    LIVE_AVAILABLE,
    IMPORT_ERR as _IMPORT_ERR,
)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

AGENT_NAME = "culture_web_agent"
# Address is derived from CULTURE_WEB_AGENT_SEED — keep this seed constant forever.
AGENT_SEED = os.getenv("CULTURE_WEB_AGENT_SEED", "quorum-culture-web-agent-phase1-seed-v1")
AGENT_PORT = 8001
AGENT_MAILBOX = True
AGENT_DESCRIPTION = (
    "Quorum Culture/Web Agent — given a Kalshi culture/entertainment market question, "
    "searches the live web (Serper + Browserbase) and returns a raw EvidenceChunk "
    "bundle of headlines, snippets and page text for a downstream compression engine."
)
COLLECT_TIMEOUT = float(os.getenv("CULTURE_AGENT_COLLECT_TIMEOUT", "30"))

# README lives next to this file. publish_agent_details=True publishes the profile
# (name/description/README) to Agentverse; the marketplace tags (innovationlab,
# hackathon) are read from the shields.io badges inside this README.
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CULTURE_WEB_README.md")

_agent_kwargs = dict(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
    description=AGENT_DESCRIPTION,
    publish_agent_details=True,  # publish profile + README -> discoverable on Agentverse/ASI:One
)
if os.path.exists(README_PATH):
    _agent_kwargs["readme_path"] = README_PATH

agent = Agent(**_agent_kwargs)


# ---------------------------------------------------------------------------
# Protocol 1: Chat Protocol v0.3.0  (ASI:One discoverable)
# ---------------------------------------------------------------------------

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """ACK immediately, collect the bundle, then reply with summary + JSON."""
    # ACK FIRST — required by the Chat Protocol spec and keeps latency low.
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    try:
        question = msg.text()
    except Exception:
        question = ""

    try:
        # async web collection with a hard timeout so the handler never hangs
        msgs, meta = await asyncio.wait_for(collect_bundle(question), timeout=COLLECT_TIMEOUT)
    except Exception as exc:
        ctx.logger.warning(f"[{AGENT_NAME}] collection failed ({exc}); using stub")
        msgs, meta = build_stub_bundle(question), {"source": "stub", "providers": []}

    reply = format_chat_reply(question, msgs, meta)
    await ctx.send(sender, ChatMessage(content=[TextContent(text=reply)]))

    ctx.logger.info(
        f"[{AGENT_NAME}] Chat reply to {sender} — {len(msgs)} chunks "
        f"(source={meta.get('source')}, providers={meta.get('providers')})"
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"[{AGENT_NAME}] ACK from {sender} for msg {msg.acknowledged_msg_id}")


# publish_manifest=True makes this agent discoverable on ASI:One
agent.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# Protocol 2: Custom evidence protocol  (orchestrator_agent.py compat)
# ---------------------------------------------------------------------------

evidence_protocol = Protocol("EvidenceCollection")


@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    """Return a real EvidenceResponse for the orchestrator pipeline."""
    ctx.logger.info(
        f"[{AGENT_NAME}] EvidenceRequest from {sender} — {msg.market_question[:60]}"
    )

    try:
        msgs, meta = await asyncio.wait_for(
            collect_bundle(msg.market_question, msg.category, msg.protected_terms),
            timeout=COLLECT_TIMEOUT,
        )
    except Exception as exc:
        ctx.logger.warning(f"[{AGENT_NAME}] collection failed ({exc}); using stub")
        msgs = build_stub_bundle(msg.market_question)

    await ctx.send(
        sender,
        EvidenceResponse(
            request_id=msg.msg_id,
            agent_name=AGENT_NAME,
            evidence_chunks=msgs,
            total_chunks=len(msgs),
        ),
    )
    ctx.logger.info(f"[{AGENT_NAME}] EvidenceResponse sent — {len(msgs)} chunks")


agent.include(evidence_protocol)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started — stable address: {agent.address}")
    ctx.logger.info(
        f"[{AGENT_NAME}] Chat Protocol v{chat_proto.spec.version} active (publish_manifest=True)"
    )
    if LIVE_AVAILABLE:
        ctx.logger.info(f"[{AGENT_NAME}] LIVE web layer ready (Serper + Browserbase)")
    else:
        ctx.logger.warning(
            f"[{AGENT_NAME}] no web provider ({_IMPORT_ERR}); serving STUB bundle only"
        )


if __name__ == "__main__":
    agent.run()