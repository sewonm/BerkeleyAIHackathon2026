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
import os
import traceback
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

# ASI:One chat protocol support (optional, gracefully degrades if unavailable)
try:
    from uagents.chat import (
        chat_protocol_spec,
        ChatMessage,
        TextContent,
        EndSessionContent,
        ChatAcknowledgement
    )
    CHAT_PROTOCOL_AVAILABLE = True
except ImportError:
    print("[Warning] Chat protocol not available - ASI:One integration disabled")
    print("Install with: pip install uagents[chat]")
    CHAT_PROTOCOL_AVAILABLE = False

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

# Create protocol for agent-to-agent communication
orchestration_protocol = Protocol("MarketOrchestration")

# Protocol for ASI:One/DeltaV interaction (if available)
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol("Chat", spec=chat_protocol_spec)

# Agent addresses — set these as env vars on Agentverse or in local .env
AGENT_ADDRESSES = {
    "culture_web": os.getenv("CULTURE_WEB_AGENT_ADDRESS"),
    "financial_research": os.getenv("FINANCIAL_RESEARCH_AGENT_ADDRESS"),
    "compression": os.getenv("COMPRESSION_AGENT_ADDRESS"),
    "decision": os.getenv("DECISION_AGENT_ADDRESS"),
}

# State storage for async coordination
analysis_state: Dict[str, dict] = {}


class PipelineState:
    """Track the state of a market analysis pipeline"""
    def __init__(self, request_id: str, market_request: "MarketRequest"):
        self.request_id = request_id
        self.market_request = market_request
        self.start_time = datetime.now()
        self.evidence_responses: List[EvidenceResponse] = []
        self.compression_response: Optional[CompressionResponse] = None
        self.decision_response: Optional[DecisionResponse] = None
        self.all_evidence_chunks: List[EvidenceChunkMsg] = []
        self.agents_used: List[str] = []
        self.requester_address: Optional[str] = None
        self.pending_agents: int = 0  # how many evidence agents we're waiting on


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
    state = PipelineState(request_id=str(msg.msg_id), market_request=msg)
    state.requester_address = sender
    analysis_state[str(msg.msg_id)] = state

    # Send initial status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Starting analysis pipeline for: {msg.market_title}"
    ))

    # Step 1: Fan out evidence requests to all available agents
    ctx.logger.info(f"[{AGENT_NAME}] Step 1: Requesting evidence from agents")

    evidence_request = EvidenceRequest(
        market_question=msg.market_question,
        market_id=msg.market_id,
        category=msg.category,
        protected_terms=msg.protected_terms,
    )

    dispatch = [
        ("culture_web", "culture_web_agent"),
        ("financial_research", "financial_research_agent"),
    ]

    for addr_key, agent_label in dispatch:
        addr = AGENT_ADDRESSES.get(addr_key)
        if addr:
            ctx.logger.info(f"[{AGENT_NAME}] Requesting evidence from {agent_label}")
            await ctx.send(addr, evidence_request)
            state.agents_used.append(agent_label)
            state.pending_agents += 1
        else:
            ctx.logger.warning(f"[{AGENT_NAME}] {agent_label} address not configured — skipping")

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


# ============================================================================
# ASI:ONE CHAT PROTOCOL HANDLER (for Agentverse/DeltaV users)
# ============================================================================

if CHAT_PROTOCOL_AVAILABLE:
    @chat_protocol.on_message(model=ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """
        Handle chat messages from Agentverse chat interface.

        Accepts JSON-formatted MarketRequest or provides help for natural language queries.
        """
        ctx.logger.info(f"[{AGENT_NAME}] Received chat message from {sender}")

        try:
            # Send acknowledgement
            await ctx.send(sender, ChatAcknowledgement())

            # Extract text from message content
            user_text = ""
            for content in msg.content:
                if isinstance(content, TextContent):
                    user_text += content.text

            ctx.logger.info(f"[{AGENT_NAME}] User query: {user_text[:200]}...")

            # Try to parse as JSON first
            try:
                request_data = json.loads(user_text)

                # Build MarketRequest from JSON
                market_request = MarketRequest(
                    market_id=request_data["market_id"],
                    market_title=request_data["market_title"],
                    market_question=request_data["market_question"],
                    category=request_data["category"],
                    current_yes_price=request_data.get("current_yes_price"),
                    current_no_price=request_data.get("current_no_price"),
                    resolution_criteria=request_data.get("resolution_criteria", ""),
                    protected_terms=request_data.get("protected_terms", [])
                )

                # Send processing notification
                response_text = f"""**Market Analysis Started**

Market: {market_request.market_title}
Category: {market_request.category}

Your analysis is being processed through the multi-agent pipeline:
1. Evidence collection from specialized agents
2. Compression of evidence context
3. Trading decision analysis
4. Final results

Results will be sent when analysis completes (typically 10-30 seconds).

**Note**: Make sure compression and decision agents are deployed with their addresses configured!
"""

                response_msg = ChatMessage(
                    content=[TextContent(text=response_text)]
                )
                await ctx.send(sender, response_msg)

                # Process the market request (this will send FinalAnalysisResult to sender)
                await handle_market_request(ctx, sender, market_request)

            except json.JSONDecodeError:
                # Not JSON - provide help message
                help_message = f"""**Orchestrator Agent - Market Analysis Pipeline**

I coordinate the full multi-agent market analysis pipeline.

**How to use me**:

Send a JSON request with market details:
```json
{{
  "market_id": "kalshi-market-123",
  "market_title": "Will France win the World Cup?",
  "market_question": "Will France win the 2026 FIFA World Cup?",
  "category": "sports",
  "current_yes_price": 0.18,
  "current_no_price": 0.82,
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "protected_terms": ["France", "World Cup", "2026"]
}}
```

**Required fields**:
- `market_id`: Unique identifier
- `market_title`: Short title
- `market_question`: Full question
- `category`: "financial", "sports", "culture", or "politics"
- `resolution_criteria`: How the market resolves

**Optional fields**:
- `current_yes_price`: Current YES price (0.0-1.0)
- `current_no_price`: Current NO price (0.0-1.0)
- `protected_terms`: Terms to preserve during compression

**What I do**:
1. 🔍 Collect evidence from specialized agents (culture, finance, news)
2. 🗜️ Compress evidence context efficiently
3. 🤔 Make trading decision recommendation
4. 📊 Return complete analysis with reasoning

**Response includes**:
- Trading recommendation (YES/NO/HOLD)
- Confidence level
- Fair probability estimate
- Key evidence points
- Compression metrics
- Processing time

**Requirements**:
- Compression agent must be deployed (standalone_compression_agent.py)
- Decision agent must be deployed (standalone_decision_agent.py)
- At least one evidence agent (financial_research_agent.py recommended)
- Agent addresses configured as environment variables

Try sending a market analysis request!
"""

                response_msg = ChatMessage(
                    content=[TextContent(text=help_message)]
                )
                await ctx.send(sender, response_msg)

            # End session
            await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))

        except Exception as e:
            ctx.logger.error(f"[{AGENT_NAME}] Error handling chat message: {str(e)}")
            ctx.logger.error(traceback.format_exc())

            error_msg = ChatMessage(
                content=[TextContent(text=f"**Error**: {str(e)}\n\nPlease check your JSON format and required fields.")]
            )
            await ctx.send(sender, error_msg)

            # End session
            await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))


# ============================================================================
# Protocol Inclusion
# ============================================================================

# Include custom protocol for agent-to-agent communication
agent.include(orchestration_protocol, publish_manifest=False)

# Include ASI:One chat protocol if available
if CHAT_PROTOCOL_AVAILABLE:
    agent.include(chat_protocol, publish_manifest=True)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Orchestrator Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to orchestrate market analysis pipelines")

    # Protocol status
    ctx.logger.info("Custom protocol: ENABLED (agent-to-agent communication)")
    if CHAT_PROTOCOL_AVAILABLE:
        ctx.logger.info("ASI:One chat protocol: ENABLED (DeltaV compatible)")
    else:
        ctx.logger.info("ASI:One chat protocol: DISABLED (install uagents[chat])")

    # TODO: In production, these would be loaded from environment or discovery
    ctx.logger.info("Note: Configure agent addresses via environment variables or Agentverse discovery")


if __name__ == "__main__":
    agent.run()
