"""
OrchestratorAgent - User-facing uAgent that coordinates the multi-agent pipeline.

This is the main entry point for users. It:
1. Receives market analysis requests
2. Coordinates evidence collection agents
3. Sends evidence to compression agent
4. Sends compressed context to decision agent
5. Returns final analysis to user

Deployable to Agentverse as the public-facing interface.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from uagents import Agent, Context, Protocol
from protocols.messages import (
    MarketRequest,
    EvidenceRequest,
    EvidenceResponse,
    EvidenceChunkMsg,
    CompressionRequest,
    CompressionResponse,
    DecisionRequest,
    DecisionResponse,
    FinalAnalysisResult,
    AgentStatus
)

# Agent configuration
AGENT_NAME = "orchestrator_agent"
AGENT_SEED = "orchestrator_agent_seed_phrase_change_in_production"
AGENT_PORT = 8000
AGENT_MAILBOX = True

# Create the agent
agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

# Create protocol
orchestration_protocol = Protocol("MarketOrchestration")

# Agent addresses - These would be published on Agentverse
# For local testing, we'll discover them dynamically
AGENT_ADDRESSES = {
    "culture_web": None,  # Will be set via environment or discovery
    "compression": None,
    "decision": None,
}

# State storage for async coordination
analysis_state: Dict[str, dict] = {}


class PipelineState:
    """Track the state of a market analysis pipeline"""
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = datetime.now()
        self.evidence_responses: List[EvidenceResponse] = []
        self.compression_response: Optional[CompressionResponse] = None
        self.decision_response: Optional[DecisionResponse] = None
        self.all_evidence_chunks: List[EvidenceChunkMsg] = []
        self.agents_used: List[str] = []
        self.requester_address: Optional[str] = None


@orchestration_protocol.on_message(model=MarketRequest)
async def handle_market_request(ctx: Context, sender: str, msg: MarketRequest):
    """
    Handle incoming market analysis requests.

    This kicks off the full pipeline:
    1. Request evidence from agents
    2. Wait for responses
    3. Compress evidence
    4. Make decision
    5. Return result

    Args:
        ctx: Agent context
        sender: Address of user/requester
        msg: Market request message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received market analysis request from {sender}")
    ctx.logger.info(f"Market: {msg.market_title}")
    ctx.logger.info(f"Category: {msg.category}")

    # Initialize pipeline state
    state = PipelineState(request_id=str(msg.msg_id))
    state.requester_address = sender
    analysis_state[str(msg.msg_id)] = state

    # Send initial status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Starting analysis pipeline for: {msg.market_title}"
    ))

    # Step 1: Request evidence from agents
    ctx.logger.info(f"[{AGENT_NAME}] Step 1: Requesting evidence from agents")

    evidence_request = EvidenceRequest(
        market_question=msg.market_question,
        category=msg.category,
        protected_terms=msg.protected_terms
    )

    # For MVP, only send to culture_web_agent
    # In production, send to multiple agents based on category
    if msg.category == "culture" or True:  # For MVP, always use culture agent
        culture_agent_addr = AGENT_ADDRESSES.get("culture_web")

        if culture_agent_addr:
            ctx.logger.info(f"[{AGENT_NAME}] Requesting evidence from culture_web_agent")
            await ctx.send(culture_agent_addr, evidence_request)
            state.agents_used.append("culture_web_agent")
        else:
            ctx.logger.warning(f"[{AGENT_NAME}] Culture web agent address not configured")

            # For local MVP, simulate evidence response
            ctx.logger.info(f"[{AGENT_NAME}] Using fallback local evidence collection")
            # This would be handled by receiving EvidenceResponse messages


@orchestration_protocol.on_message(model=EvidenceResponse)
async def handle_evidence_response(ctx: Context, sender: str, msg: EvidenceResponse):
    """
    Handle evidence responses from collection agents.

    Args:
        ctx: Agent context
        sender: Address of evidence agent
        msg: Evidence response message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received evidence from {msg.agent_name}")
    ctx.logger.info(f"Evidence chunks: {msg.total_chunks}")

    # Find the corresponding request state
    request_id = str(msg.request_id)
    state = analysis_state.get(request_id)

    if not state:
        ctx.logger.warning(f"[{AGENT_NAME}] No state found for request {request_id}")
        return

    # Store evidence response
    state.evidence_responses.append(msg)
    state.all_evidence_chunks.extend(msg.evidence_chunks)

    # Check if we have all evidence we're waiting for
    # For MVP, we only request from one agent, so proceed immediately
    ctx.logger.info(f"[{AGENT_NAME}] Step 2: Compressing evidence")

    # Send evidence to compression agent
    compression_request = CompressionRequest(
        market_question="Market analysis",  # Would use actual market question
        protected_terms=[],  # Would use actual protected terms
        evidence_chunks=state.all_evidence_chunks,
        token_budget=3000
    )

    compression_agent_addr = AGENT_ADDRESSES.get("compression")
    if compression_agent_addr:
        await ctx.send(compression_agent_addr, compression_request)
    else:
        ctx.logger.warning(f"[{AGENT_NAME}] Compression agent address not configured")


@orchestration_protocol.on_message(model=CompressionResponse)
async def handle_compression_response(ctx: Context, sender: str, msg: CompressionResponse):
    """
    Handle compression response.

    Args:
        ctx: Agent context
        sender: Address of compression agent
        msg: Compression response message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received compression result")
    ctx.logger.info(f"Compression ratio: {msg.compression_ratio:.2f}x")

    # Find state
    request_id = str(msg.request_id)
    state = analysis_state.get(request_id)

    if not state:
        ctx.logger.warning(f"[{AGENT_NAME}] No state found for request {request_id}")
        return

    state.compression_response = msg

    # Step 3: Send to decision agent
    ctx.logger.info(f"[{AGENT_NAME}] Step 3: Making decision")

    decision_request = DecisionRequest(
        market_title="Market Title",  # Would use actual market data
        market_question="Market Question",
        current_yes_price=0.5,
        compressed_context=msg.compressed_context,
        kept_chunks_count=msg.kept_chunks_count
    )

    decision_agent_addr = AGENT_ADDRESSES.get("decision")
    if decision_agent_addr:
        await ctx.send(decision_agent_addr, decision_request)
    else:
        ctx.logger.warning(f"[{AGENT_NAME}] Decision agent address not configured")


@orchestration_protocol.on_message(model=DecisionResponse)
async def handle_decision_response(ctx: Context, sender: str, msg: DecisionResponse):
    """
    Handle decision response and send final result to user.

    Args:
        ctx: Agent context
        sender: Address of decision agent
        msg: Decision response message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received decision: {msg.recommendation}")
    ctx.logger.info(f"Confidence: {msg.confidence:.2%}")

    # Find state
    request_id = str(msg.request_id)
    state = analysis_state.get(request_id)

    if not state:
        ctx.logger.warning(f"[{AGENT_NAME}] No state found for request {request_id}")
        return

    state.decision_response = msg

    # Calculate processing time
    processing_time = (datetime.now() - state.start_time).total_seconds()

    # Build final result
    final_result = FinalAnalysisResult(
        market_title="Market Analysis",  # Would use actual market title
        raw_token_count=state.compression_response.raw_token_count if state.compression_response else 0,
        compressed_token_count=state.compression_response.compressed_token_count if state.compression_response else 0,
        compression_ratio=state.compression_response.compression_ratio if state.compression_response else 0.0,
        recommendation=msg.recommendation,
        confidence=msg.confidence,
        fair_probability=msg.fair_probability,
        reasoning=msg.reasoning,
        key_evidence=msg.key_evidence,
        missing_info=msg.missing_info,
        agents_used=state.agents_used,
        processing_time_seconds=processing_time
    )

    # Send final result to requester
    if state.requester_address:
        ctx.logger.info(f"[{AGENT_NAME}] Sending final result to requester")
        await ctx.send(state.requester_address, final_result)

    # Send completion status
    await ctx.send(state.requester_address, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Analysis complete: {msg.recommendation} ({msg.confidence:.0%} confidence)"
    ))

    # Clean up state
    del analysis_state[request_id]


# Include protocol
agent.include(orchestration_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Orchestrator Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to orchestrate market analysis pipelines")

    # TODO: In production, these would be loaded from environment or discovery
    ctx.logger.info("Note: Configure agent addresses via environment variables or Agentverse discovery")


if __name__ == "__main__":
    agent.run()
