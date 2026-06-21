"""
SportsVideoAgent — Deployed Fetch.ai uAgent for sports evidence (live-stats stub, Phase 1).

Address is derived from AGENT_SEED — keep this seed constant forever (SA-AGENT-01).
A fixed seed produces a byte-for-byte identical agent1q… address across every restart.

Dual-protocol agent:
  1. Chat Protocol v0.3.0 (SA-AGENT-03, ASI:One discoverable via publish_manifest=True)
     — receives a ChatMessage, acks it, then replies with a JSON-serialised stub
       EvidenceChunkMsg bundle.
  2. Custom SportsVideoEvidence protocol (orchestrator_agent.py compat)
     — receives EvidenceRequest, returns EvidenceResponse with the same stub bundle.

AGENTVERSE COPY-PASTE SAFE: no app-package imports.
Only uagents, uagents_core, stdlib, and protocols.messages are used.
"""

import os
import json
from datetime import datetime, timezone

from uagents import Agent, Context, Protocol
from protocols.messages import (
    EvidenceRequest,
    EvidenceResponse,
    EvidenceChunkMsg,
    AgentStatus,
)
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

# ---------------------------------------------------------------------------
# Module constants  (mirror culture_web_agent.py conventions)
# ---------------------------------------------------------------------------

AGENT_NAME = "sports_video_agent"
# Address is derived from AGENT_SEED — keep this seed constant forever (SA-AGENT-01).
AGENT_SEED = os.getenv("SPORTS_VIDEO_AGENT_SEED", "quorum-sports-agent-phase1-seed-v1")
AGENT_PORT = 8004
AGENT_MAILBOX = True

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

# ---------------------------------------------------------------------------
# Inline stub-bundle builder (Phase 1 — same bundle returned by both protocols)
# ---------------------------------------------------------------------------

def build_stub_bundle(market_question: str) -> list:
    """
    Return a canned list of EvidenceChunkMsgs.

    Phase 1 stub — does NOT call any external API.  The four required metadata
    keys (kind / fetched_via / source_strength / observed_at) are all present
    in each chunk so downstream consumers can validate the schema.
    """
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    question_preview = (market_question or "")[:60]
    return [
        EvidenceChunkMsg(
            source_type="sports_video",
            text=f"(stub) Argentina 2-1 Brazil — re: {question_preview}",
            source_url="stub://sports/phase1",
            confidence=0.5,
            metadata={
                "kind": "scoreline",
                "fetched_via": "stub",
                "source_strength": "stub",
                "observed_at": observed_at,
            },
        ),
        EvidenceChunkMsg(
            source_type="sports_video",
            text="(stub) Star striker listed as questionable with an ankle knock.",
            source_url="stub://sports/phase1",
            confidence=0.5,
            metadata={
                "kind": "injury",
                "fetched_via": "stub",
                "source_strength": "stub",
                "observed_at": observed_at,
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Protocol 1: Chat Protocol v0.3.0  (SA-AGENT-03)
# ---------------------------------------------------------------------------

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Ack the incoming ChatMessage, then reply with the JSON stub bundle."""
    # ACK FIRST — required by Chat Protocol spec
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    try:
        question = msg.text()
    except Exception:
        question = ""

    chunks = build_stub_bundle(question)
    bundle_json = json.dumps([c.model_dump() for c in chunks])

    await ctx.send(sender, ChatMessage(content=[TextContent(text=bundle_json)]))

    ctx.logger.info(
        f"[{AGENT_NAME}] Chat reply sent to {sender} — {len(chunks)} chunks"
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    """Log acknowledgements received from the other side."""
    ctx.logger.info(
        f"[{AGENT_NAME}] ACK from {sender} for msg {msg.acknowledged_msg_id}"
    )


# publish_manifest=True makes this agent discoverable on ASI:One (Plan 03 prerequisite)
agent.include(chat_proto, publish_manifest=True)


# ---------------------------------------------------------------------------
# Protocol 2: Custom evidence protocol  (orchestrator_agent.py compat)
# ---------------------------------------------------------------------------

evidence_protocol = Protocol("SportsVideoEvidence")


@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    """
    Return a stub EvidenceResponse so orchestrator_agent.py keeps working.

    Upgraded from the previous "error AgentStatus" placeholder to a real response.
    """
    ctx.logger.info(
        f"[{AGENT_NAME}] EvidenceRequest from {sender} — question: {msg.market_question[:60]}"
    )

    chunks = build_stub_bundle(msg.market_question)

    await ctx.send(
        sender,
        EvidenceResponse(
            request_id=msg.msg_id,
            agent_name=AGENT_NAME,
            evidence_chunks=chunks,
            total_chunks=len(chunks),
        ),
    )

    ctx.logger.info(
        f"[{AGENT_NAME}] EvidenceResponse sent — {len(chunks)} stub chunks"
    )


agent.include(evidence_protocol)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started — stable address: {agent.address}")
    ctx.logger.info(
        f"[{AGENT_NAME}] Chat Protocol v{chat_proto.spec.version} active "
        f"(publish_manifest=True)"
    )
    ctx.logger.info(
        f"[{AGENT_NAME}] SportsVideoEvidence protocol active (orchestrator compat)"
    )


if __name__ == "__main__":
    agent.run()
