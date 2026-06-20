"""
SportsVideoAgent - PLACEHOLDER for future implementation.

This agent would collect evidence from sports videos, press conferences,
and sports-related sources.

Deployable to Agentverse once implemented.
"""

from uagents import Agent, Context, Protocol
from protocols.messages import EvidenceRequest, EvidenceResponse, AgentStatus

# Agent configuration
AGENT_NAME = "sports_video_agent"
AGENT_SEED = "sports_video_agent_seed_phrase_change_in_production"
AGENT_PORT = 8004
AGENT_MAILBOX = True

# Create the agent
agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

evidence_protocol = Protocol("SportsVideoEvidence")


@evidence_protocol.on_message(model=EvidenceRequest)
async def handle_evidence_request(ctx: Context, sender: str, msg: EvidenceRequest):
    """Handle evidence requests - PLACEHOLDER"""
    ctx.logger.info(f"[{AGENT_NAME}] Received request (NOT IMPLEMENTED)")

    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="error",
        message="Sports video agent not implemented yet"
    ))

    # TODO: Implement sports video evidence collection
    # Would integrate with video APIs, transcription services, etc.


agent.include(evidence_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started (PLACEHOLDER)")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.warning("TODO: Implement sports video evidence collection")


if __name__ == "__main__":
    agent.run()
