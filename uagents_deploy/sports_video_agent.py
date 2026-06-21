"""
SportsVideoAgent — Deployed Fetch.ai uAgent for live sports evidence.

Address is derived from AGENT_SEED — keep this seed constant forever (SA-AGENT-01).
A fixed seed produces a byte-for-byte identical agent1q… address across every restart.

Dual-protocol agent:
  1. Chat Protocol v0.3.0 (SA-AGENT-03, ASI:One discoverable via publish_manifest=True)
     — receives a ChatMessage with a market question, ACKs immediately, then replies
       with a human-readable evidence summary + the full JSON bundle.
  2. Custom SportsVideoEvidence protocol (orchestrator_agent.py compat)
     — receives EvidenceRequest, returns EvidenceResponse with the same bundle.

LIVE DATA (Phase 5): this is a MAILBOX agent — it runs locally, so it imports the
project's collectors (app.services.*) and returns REAL evidence:
  * ESPN HTTP anchor (Phase 2): score/state, box stats, event log, odds w/ line
    movement, win/implied probability, injuries, lineups — for ANY sport.
  * Browserbase noisy layer (Phase 3): raw scraped text (ships from fixtures).
Blocking HTTP/scrape runs off the event loop via asyncio.to_thread (SA-INT-02) and
the handler ACKs first (SA-INT-01). If live data is unavailable, it degrades to
recorded fixtures, then to a tiny stub bundle — the demo NEVER returns nothing
(SA-INT-02 demo-safety). If the app package can't be imported, it still runs on the
stub bundle alone.

DEPLOY AS A MAILBOX AGENT (mailbox=True): run this file locally
    python uagents_deploy/sports_video_agent.py
then open the Agent Inspector link printed in the terminal -> Connect -> Mailbox ->
Finish. That connects it to Agentverse and makes it discoverable on ASI:One.
"""

import os
import asyncio

# Load .env (repo root) so BROWSERBASE_API_KEY / SPORTS_VIDEO_AGENT_SEED / etc. are
# available when the agent runs locally — must happen before any os.getenv below.
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

# Bundle-building logic lives in sports_evidence.py (importable + unit-testable
# without constructing a uAgent). It imports the project collectors for LIVE data.
from sports_evidence import (
    collect_bundle,
    build_stub_bundle,
    format_chat_reply,
    LIVE_AVAILABLE,
    IMPORT_ERR as _IMPORT_ERR,
)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

AGENT_NAME = "sports_video_agent"
# Address is derived from AGENT_SEED — keep this seed constant forever (SA-AGENT-01).
AGENT_SEED = os.getenv("SPORTS_VIDEO_AGENT_SEED", "quorum-sports-agent-phase1-seed-v1")
AGENT_PORT = 8004
AGENT_MAILBOX = True
AGENT_DESCRIPTION = (
    "Quorum Sports Agent — given a Kalshi sports market question, resolves the "
    "sport/league + live game and returns a wide raw EvidenceChunk bundle (live "
    "ESPN stats + odds + win-prob + injuries/lineups, plus noisy scraped text)."
)
COLLECT_TIMEOUT = float(os.getenv("SPORTS_AGENT_COLLECT_TIMEOUT", "30"))

# README lives next to this file. publish_agent_details=True publishes the profile
# (name/description/README) to Agentverse; the marketplace tags (innovationlab,
# hackathon) are read from the shields.io badges inside this README.
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SPORTS_AGENT_README.md")

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
# Protocol 1: Chat Protocol v0.3.0  (SA-AGENT-03 / SA-INT-01 / SA-INT-02)
# ---------------------------------------------------------------------------

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """ACK immediately, collect off the event loop, then reply with the bundle."""
    # ACK FIRST — required by Chat Protocol spec and keeps latency low (SA-INT-01/02)
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    try:
        question = msg.text()
    except Exception:
        question = ""

    try:
        # blocking HTTP/scrape OFF the event loop, with a hard timeout (SA-INT-02)
        msgs, meta = await asyncio.wait_for(
            asyncio.to_thread(collect_bundle, question), timeout=COLLECT_TIMEOUT
        )
    except Exception as exc:
        ctx.logger.warning(f"[{AGENT_NAME}] collection failed ({exc}); using stub")
        msgs, meta = build_stub_bundle(question), {"source": "stub"}

    reply = format_chat_reply(question, msgs, meta)
    await ctx.send(sender, ChatMessage(content=[TextContent(text=reply)]))

    ctx.logger.info(
        f"[{AGENT_NAME}] Chat reply to {sender} — {len(msgs)} chunks "
        f"(source={meta.get('source')}, sport={meta.get('sport')})"
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"[{AGENT_NAME}] ACK from {sender} for msg {msg.acknowledged_msg_id}")


# publish_manifest=True makes this agent discoverable on ASI:One
agent.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# Protocol 2: Custom evidence protocol  (orchestrator_agent.py compat)
# ---------------------------------------------------------------------------

evidence_protocol = Protocol("SportsVideoEvidence")


@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    """Return a real EvidenceResponse for the orchestrator pipeline."""
    ctx.logger.info(
        f"[{AGENT_NAME}] EvidenceRequest from {sender} — {msg.market_question[:60]}"
    )

    try:
        msgs, meta = await asyncio.wait_for(
            asyncio.to_thread(collect_bundle, msg.market_question, msg.category),
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
        ctx.logger.info(f"[{AGENT_NAME}] LIVE data layer ready (ESPN anchor + noisy)")
    else:
        ctx.logger.warning(
            f"[{AGENT_NAME}] app package not importable ({_IMPORT_ERR}); serving STUB bundle only"
        )


if __name__ == "__main__":
    agent.run()
