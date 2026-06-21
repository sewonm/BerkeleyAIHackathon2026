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
AGENT_SEED = "11bf23bf45f76363d673a7f453c393ba5e5920c91418427c9d44dcff20021437"
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
    "sports_video": os.getenv("SPORTS_VIDEO_AGENT_ADDRESS"),
    "compression": os.getenv("COMPRESSION_AGENT_ADDRESS"),
    "decision": os.getenv("DECISION_AGENT_ADDRESS"),
    "kalshi": os.getenv("KALSHI_AGENT_ADDRESS"),
}

# State storage for async coordination
analysis_state: Dict[str, dict] = {}

# State storage for pending trade confirmations
pending_confirmations: Dict[str, dict] = {}  # sender_address -> {decision_response, market_request, timestamp}


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

    try:
        from redis_service import get_compressed
        cached = get_compressed(msg.market_id)
        if cached:
            ctx.logger.info(f"[{AGENT_NAME}] Cache hit for {msg.market_id} — skipping pipeline")
            await ctx.send(sender, AgentStatus(
                agent_name=AGENT_NAME,
                status="completed",
                message=f"Returning cached result for {msg.market_id}"
            ))
            await ctx.send(sender, FinalAnalysisResult(**cached))
            return
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Redis cache check skipped: {e}")

    try:
        from agent_memory_service import search_past_decisions
        past = search_past_decisions(msg.market_question, limit=3)
        if past:
            ctx.logger.info(f"[{AGENT_NAME}] Found {len(past)} past decisions for similar markets")
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Agent Memory search skipped: {e}")

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
        ("sports_video", "sports_video_agent"),
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
    Handle decision response and send confirmation prompt to user.

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

    # Store pending confirmation
    if state.requester_address:
        pending_confirmations[state.requester_address] = {
            "decision_response": msg,
            "market_request": state.market_request,
            "compression_response": state.compression_response,
            "agents_used": state.agents_used,
            "processing_time": processing_time,
            "timestamp": datetime.now()
        }

        # Send decision result with confirmation prompt via chat
        if CHAT_PROTOCOL_AVAILABLE:
            evidence_summary = "\n".join([f"• {e}" for e in msg.key_evidence[:5]])
            missing_info_text = ""
            if msg.missing_info:
                missing_info_text = f"\n\n**Missing Information:**\n" + "\n".join([f"• {m}" for m in msg.missing_info[:3]])

            decision_text = f"""📊 **Trading Decision Analysis Complete**

**Question:** {state.market_request.market_question}

**Recommendation:** **{msg.recommendation}**
**Confidence:** {msg.confidence:.1%}
**Fair Probability:** {msg.fair_probability:.1%}

**Reasoning:**
{msg.reasoning}

**Key Supporting Evidence:**
{evidence_summary}
{missing_info_text}

**Analysis Metrics:**
• Agents used: {', '.join(state.agents_used)}
• Processing time: {processing_time:.1f}s
• Evidence compressed: {state.compression_response.compression_ratio:.1f}x ratio

---

⚠️ **Do you want to execute this trade on Kalshi?**

Reply **'yes'** to execute the trade or **'no'** to cancel.

_(This confirmation will expire in 5 minutes)_
"""

            confirmation_msg = ChatMessage(
                content=[TextContent(text=decision_text)]
            )
            await ctx.send(state.requester_address, confirmation_msg)
            ctx.logger.info(f"[{AGENT_NAME}] Sent confirmation prompt to {state.requester_address}")

        # Also send status update
        await ctx.send(state.requester_address, AgentStatus(
            agent_name=AGENT_NAME,
            status="awaiting_confirmation",
            message=f"Decision ready: {msg.recommendation} ({msg.confidence:.0%} confidence) - awaiting your confirmation"
        ))

    # Don't clean up state yet - keep it for confirmation handling
    # Will clean up after user confirms/cancels or timeout


# ============================================================================
# ASI:ONE CHAT PROTOCOL HANDLER (for Agentverse/DeltaV users)
# ============================================================================

def detect_category(question: str) -> str:
    """Detect market category from natural language question."""
    question_lower = question.lower()

    # Sports keywords
    sports_keywords = [
        "win", "beat", "defeat", "champion", "game", "match", "score", "team",
        "nba", "nfl", "mlb", "nhl", "fifa", "world cup", "olympics", "super bowl",
        "lakers", "celtics", "chiefs", "patriots", "yankees", "dodgers",
        "soccer", "football", "basketball", "baseball", "hockey", "tennis"
    ]

    # Financial keywords
    financial_keywords = [
        "bitcoin", "btc", "eth", "ethereum", "crypto", "stock", "sp500", "s&p",
        "price", "dollar", "usd", "$", "market", "trading", "nasdaq", "dow"
    ]

    # Check for sports
    if any(keyword in question_lower for keyword in sports_keywords):
        return "sports"

    # Check for financial
    if any(keyword in question_lower for keyword in financial_keywords):
        return "financial"

    # Default to culture
    return "culture"


if CHAT_PROTOCOL_AVAILABLE:
    @chat_protocol.on_message(model=ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """
        Handle natural language questions from users.

        Example: "will france win the worldcup 2026"

        Flow:
        1. Parse natural language question
        2. Route to appropriate evidence agents (sports, financial, etc.)
        3. Compress evidence
        4. Get decision recommendation
        5. Ask user for trade confirmation
        6. Execute on Kalshi if confirmed
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

            user_text = user_text.strip()
            ctx.logger.info(f"[{AGENT_NAME}] User question: {user_text}")

            # Check if this is a confirmation response (yes/no)
            if sender in pending_confirmations:
                user_response = user_text.lower()

                if user_response in ["yes", "y", "confirm", "execute"]:
                    ctx.logger.info(f"[{AGENT_NAME}] User confirmed trade execution")

                    # Get pending confirmation data
                    confirmation_data = pending_confirmations[sender]
                    decision = confirmation_data["decision_response"]
                    market_req = confirmation_data["market_request"]

                    # Send to Kalshi agent for execution
                    kalshi_agent_addr = AGENT_ADDRESSES.get("kalshi")
                    if kalshi_agent_addr:
                        # Import the ExecuteTradeRequest message type
                        from protocols.messages import ExecuteTradeRequest

                        trade_request = ExecuteTradeRequest(
                            market_id=market_req.market_id,
                            market_title=market_req.market_title,
                            action=decision.recommendation,  # YES/NO
                            side="yes" if decision.recommendation == "YES" else "no",
                            quantity=1,  # Default to 1 contract
                            fair_probability=decision.fair_probability,
                            confidence=decision.confidence
                        )

                        await ctx.send(kalshi_agent_addr, trade_request)

                        await ctx.send(sender, ChatMessage(
                            content=[TextContent(text=f"✅ **Trade execution initiated**\n\nSending {decision.recommendation} trade to Kalshi agent...\n\nYou will receive confirmation once the trade is executed.")]
                        ))
                        ctx.logger.info(f"[{AGENT_NAME}] Trade request sent to Kalshi agent")
                    else:
                        await ctx.send(sender, ChatMessage(
                            content=[TextContent(text="❌ **Kalshi agent not configured**\n\nCannot execute trade - KALSHI_AGENT_ADDRESS not set.")]
                        ))
                        ctx.logger.warning(f"[{AGENT_NAME}] Kalshi agent address not configured")

                    # Clean up pending confirmation
                    del pending_confirmations[sender]

                    # End session
                    await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
                    return

                elif user_response in ["no", "n", "cancel", "abort"]:
                    ctx.logger.info(f"[{AGENT_NAME}] User cancelled trade execution")

                    await ctx.send(sender, ChatMessage(
                        content=[TextContent(text="❌ **Trade cancelled**\n\nNo trade will be executed. Analysis results have been saved for your reference.")]
                    ))

                    # Clean up pending confirmation
                    del pending_confirmations[sender]

                    # End session
                    await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
                    return
                else:
                    # Invalid response - ask again
                    await ctx.send(sender, ChatMessage(
                        content=[TextContent(text=f"⚠️ **Invalid response: '{user_text}'**\n\nPlease reply **'yes'** to execute the trade or **'no'** to cancel.")]
                    ))
                    return

            # Handle empty or help requests
            if not user_text or user_text.lower() in ["help", "?", "how", "what"]:
                help_message = f"""**Orchestrator Agent - Prediction Market Analysis**

I analyze prediction markets and help you make informed trading decisions!

**How to use me**:

Just ask me a natural language question about any prediction market:

**Sports examples:**
- "Will France win the World Cup 2026?"
- "Will Lakers beat the Celtics?"
- "Will Argentina beat Brazil in the next World Cup qualifier?"

**Financial examples:**
- "Will Bitcoin reach $100k by end of 2026?"
- "Will S&P 500 close above 5000?"
- "Will Ethereum reach $10k?"

**What I do**:
1. 🔍 Auto-detect category (sports, financial, culture)
2. 📊 Gather evidence from specialized agents (ESPN stats, Kalshi data, web sources)
3. 🗜️ Compress and analyze all evidence
4. 🤔 Generate trading recommendation (YES/NO/HOLD)
5. ✅ Ask for your confirmation before executing any trades

**Response includes**:
- Trading recommendation with confidence level
- Fair probability estimate
- Key supporting evidence
- Missing information to consider
- Opportunity to confirm or cancel the trade

**Requirements**:
- Evidence agents (sports, financial) collect live data
- Compression agent analyzes context
- Decision agent generates recommendations
- Kalshi agent executes trades (only with your approval)

Try asking me a prediction market question!
"""

                response_msg = ChatMessage(
                    content=[TextContent(text=help_message)]
                )
                await ctx.send(sender, response_msg)
                # End session after help
                await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
                return

            # Process natural language question
            ctx.logger.info(f"[{AGENT_NAME}] Processing natural language question")

            # Auto-detect category
            category = detect_category(user_text)
            ctx.logger.info(f"[{AGENT_NAME}] Category detected: {category}")

            # Send initial processing notification
            await ctx.send(sender, ChatMessage(
                content=[TextContent(text=f"🔍 **Analyzing your question**\n\nQuestion: {user_text}\nCategory: {category}\n\nGathering evidence from specialized agents...")]
            ))

            # Create a MarketRequest from the natural language question
            from uuid import uuid4
            market_request = MarketRequest(
                market_id=f"chat-{uuid4()}",
                market_title=user_text[:100],  # Use question as title
                market_question=user_text,
                category=category,
                resolution_criteria="To be determined by evidence analysis",
                protected_terms=[],  # Will be extracted by agents
                current_yes_price=0.5,  # Default middle price
                current_no_price=0.5,
            )

            # Process through the pipeline by calling the existing handler
            # We'll use the request_id to track this for the user
            await handle_market_request(ctx, sender, market_request)

            ctx.logger.info(f"[{AGENT_NAME}] Natural language request initiated: {market_request.msg_id}")

            # Don't end session yet - wait for pipeline to complete
            # Session will be ended after final result

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
