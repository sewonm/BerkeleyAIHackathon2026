"""
CultureWebAgent - Standalone uAgent for culture/entertainment evidence collection.

This agent can be deployed to Agentverse and will respond to evidence requests
by collecting culture/web-related information.

For MVP: Reads from local sample file
For Production: Would integrate with Browserbase for live web scraping
"""

import os
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


def collect_culture_evidence(market_question: str, protected_terms: list) -> list:
    """
    Collect culture/entertainment evidence.

    For MVP: Reads from local sample file
    For Production: Would use Browserbase to scrape live sources

    Args:
        market_question: The market question to research
        protected_terms: Important terms to look for

    Returns:
        List of evidence chunks
    """
    # For MVP: Read from local sample file
    sample_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "examples",
        "raw_context",
        "culture_web_context.txt"
    )

    if not os.path.exists(sample_file_path):
        print(f"[{AGENT_NAME}] Warning: Sample file not found at {sample_file_path}")
        return []

    with open(sample_file_path, 'r') as f:
        raw_text = f.read()

    # Simple chunking by paragraphs
    paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]

    # Convert to evidence chunks
    evidence_chunks = []
    for para in paragraphs[:50]:  # Limit to 50 chunks for demo
        if len(para.split()) < 10:  # Skip very short paragraphs
            continue

        chunk = EvidenceChunkMsg(
            source_type="culture_web",
            text=para,
            source_url="local://examples/raw_context/culture_web_context.txt",
            confidence=0.8,
            metadata={"agent": AGENT_NAME, "is_sample_data": True}
        )
        evidence_chunks.append(chunk)

    return evidence_chunks


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
