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
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional

# Load .env into the process environment for LOCAL / mailbox runs.
# The app reads all config via os.getenv; without this, keys sitting in .env
# (ASI1_API_KEY, agent addresses) are invisible — routing silently falls back to
# the heuristic tier and the startup log prints "LLM DISABLED".
# Skipped under pytest: importing this module must not leak real .env secrets into
# the test process (tests assert keyless/heuristic behavior with a clean env).
# Guarded so a missing python-dotenv (e.g. an Agentverse-hosted runtime) never
# crashes import.
if "pytest" not in sys.modules:
    try:
        from dotenv import load_dotenv
        load_dotenv()  # walks up from this file to repo-root .env; no-op if absent
    except ImportError:
        pass

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
    from uagents_core.contrib.protocols.chat import (
        chat_protocol_spec,
        ChatMessage,
        TextContent,
        EndSessionContent,
        ChatAcknowledgement,
    )
    CHAT_PROTOCOL_AVAILABLE = True
except ImportError:
    print("[Warning] Chat protocol not available - ASI:One integration disabled")
    CHAT_PROTOCOL_AVAILABLE = False

# Router import (Phase 2 deliverable — guarded so a missing router never crashes the agent)
try:
    from router import route as router_route, _route_heuristic, CATEGORY_TO_AGENT
    ROUTER_AVAILABLE = True
except Exception as _router_err:   # never crash the agent if router import fails
    ROUTER_AVAILABLE = False
    router_route = None
    _route_heuristic = None
    CATEGORY_TO_AGENT = {}

# Agent configuration
AGENT_NAME = "orchestrator_agent"
# Address is derived from AGENT_SEED — keep this seed constant + UNIQUE (a shared
# placeholder collides on Agentverse: "seed phrase already used by another user").
# Real value lives in .env (gitignored); the default is only a local fallback.
AGENT_SEED = os.getenv("ORCHESTRATOR_AGENT_SEED", "quorum-orchestrator-agent-seed-v1")
AGENT_PORT = 8000
AGENT_MAILBOX = True

# Profile published to Agentverse/ASI:One so the router can match plain-language
# market questions to this agent (intent discovery). publish_agent_details=True
# publishes name/description/README; marketplace tags come from the README badges.
AGENT_DESCRIPTION = (
    "Quorum Orchestrator — the front door for prediction-market questions. Routes a "
    "messy natural-language market question (sports / financial / culture / politics) "
    "to the right specialized research agent and returns the routing decision plus the "
    "collected evidence analysis."
)
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ORCHESTRATOR_README.md")

# Tunable LLM router timeout (seconds). Degrades to instant heuristic on expiry (SAFETY-03).
ROUTER_TIMEOUT = float(os.getenv("ROUTER_TIMEOUT", "8.0"))

# Create the agent
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

# Create protocol for agent-to-agent communication
orchestration_protocol = Protocol("MarketOrchestration")

# Protocol for ASI:One/DeltaV interaction (if available)
# Use spec= only (no explicit name) — matches sports_video_agent.py pattern and avoids
# "spec name overrides given name" warning + Protocol.verify() failure.
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol(spec=chat_protocol_spec)

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


# ============================================================================
# EXTRACTED SYNC HELPERS — module-scope, importable + unit-testable without
# constructing a uAgent (uagents_deploy/ on sys.path is sufficient).
# These contain all the testable logic; the async handler stays thin.
# ============================================================================

def _heuristic_fallback(user_text: str):
    """Instant, no-network fallback used on router timeout/error (SAFETY-03).
    Delegates to the imported _route_heuristic; never touches the network."""
    return _route_heuristic(user_text)


def _build_market_request_from_decision(user_text: str, decision) -> MarketRequest:
    """DISPATCH-01: map RouterDecision onto the existing MarketRequest fields — no protocol change.
      decision.rewritten_query -> market_question
      decision.category        -> category
      decision.protected_terms -> protected_terms
    """
    from uuid import uuid4 as _uuid4
    return MarketRequest(
        market_id=f"chat-{_uuid4()}",
        market_title=user_text[:100],
        market_question=decision.rewritten_query,       # rewritten_query -> market_question
        category=decision.category,                     # category -> category
        protected_terms=list(decision.protected_terms), # protected_terms -> protected_terms
        resolution_criteria="To be determined by evidence analysis",
        current_yes_price=0.5,
        current_no_price=0.5,
    )


def _format_routing_note(decision) -> str:
    """DISPATCH-04: user-visible note naming the chosen category, tier, confidence, rationale."""
    return (
        f"Routing to: {decision.category} agent "
        f"(via {decision.tier}, {decision.confidence:.0%} confidence)\n"
        f"Rationale: {decision.rationale}"
    )


def _format_evidence_digest(state, max_chunks: int = 8, snippet_len: int = 240) -> str:
    """DEMO FALLBACK: render collected evidence chunks into a readable chat reply for the
    user when the downstream compression/decision agents are not wired. Category-agnostic —
    works for any evidence agent. Remove once the full pipeline is connected."""
    chunks = state.all_evidence_chunks
    mr = state.market_request
    agents = ", ".join(state.agents_used) or "evidence agent"

    # Count chunks by source strength (anchor/noisy/...) falling back to source_type.
    by_strength: dict[str, int] = {}
    for c in chunks:
        key = (c.metadata or {}).get("source_strength") or c.source_type
        by_strength[key] = by_strength.get(key, 0) + 1
    breakdown = " / ".join(f"{n} {k}" for k, n in by_strength.items()) or "0"

    lines = [
        f"📊 **Evidence collected for:** {mr.market_question}",
        f"**Category:** {mr.category} · **Agent(s):** {agents} · "
        f"**{len(chunks)} chunk(s)** ({breakdown})",
        "_Downstream compression/decision agents aren't wired yet — showing the raw evidence digest._",
        "",
        "**Top evidence:**",
    ]
    for c in chunks[:max_chunks]:
        kind = (c.metadata or {}).get("kind") or c.source_type
        text = " ".join((c.text or "").split())
        if len(text) > snippet_len:
            text = text[:snippet_len].rstrip() + "…"
        lines.append(f"• [{kind}] {text}")
    if len(chunks) > max_chunks:
        lines.append(f"…and {len(chunks) - max_chunks} more chunk(s).")
    return "\n".join(lines)


def _resolve_dispatch(category: str):
    """DISPATCH-02/03: resolve a routed category to (target_key, address).
    Returns (None, None) when the category has no wired agent (politics/none),
    or (target_key, None) when the key exists but its address env var is unset."""
    target_key = CATEGORY_TO_AGENT.get(category)   # None for politics/none
    if target_key is None:
        return None, None
    return target_key, AGENT_ADDRESSES.get(target_key)


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

    # Step 1: Dispatch evidence request to the single chosen agent (DISPATCH-02)
    ctx.logger.info(f"[{AGENT_NAME}] Step 1: Requesting evidence from chosen agent")

    # Build the EvidenceRequest from the already-router-mapped MarketRequest fields
    # (DISPATCH-01 done in plan 01 — no protocol change here)
    evidence_request = EvidenceRequest(
        msg_id=msg.msg_id,   # reuse MarketRequest id so EvidenceResponse.request_id correlates to pipeline state
        market_question=msg.market_question,
        market_id=msg.market_id,
        category=msg.category,
        protected_terms=msg.protected_terms,
    )

    target_key, addr = _resolve_dispatch(msg.category)

    if target_key is None or not addr:
        # DISPATCH-03 — unwired category (politics/none) OR unset address: clean handoff, no hang
        handoff_text = (
            f"Routed to {msg.category}"
            + (f" ({target_key})" if target_key else "")
            + " — no live agent wired yet for this category."
        )
        ctx.logger.info("[%s] %s — clean handoff (no wired agent)", AGENT_NAME, handoff_text)
        if state.requester_address and CHAT_PROTOCOL_AVAILABLE:
            await ctx.send(state.requester_address, ChatMessage(content=[TextContent(text=handoff_text)]))
            await ctx.send(state.requester_address, ChatMessage(content=[EndSessionContent()]))
        analysis_state.pop(str(msg.msg_id), None)   # guard: no stale state -> no pending_agents==0 hang
        return

    # DISPATCH-02 — single-agent dispatch (exactly one send, not three)
    ctx.logger.info("[%s] Dispatching to single agent: %s", AGENT_NAME, target_key)
    await ctx.send(addr, evidence_request)
    state.agents_used.append(target_key)
    state.pending_agents = 1


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
    compression_agent_addr = AGENT_ADDRESSES.get("compression")
    if compression_agent_addr:
        # Step 2: compress evidence -> (later) decision -> confirmation (full pipeline)
        ctx.logger.info(f"[{AGENT_NAME}] Step 2: Compressing evidence")
        compression_request = CompressionRequest(
            market_question=state.market_request.market_question,
            protected_terms=list(state.market_request.protected_terms),
            evidence_chunks=state.all_evidence_chunks,
            token_budget=3000,
        )
        await ctx.send(compression_agent_addr, compression_request)
    else:
        # DEMO FALLBACK (compression/decision agents unwired): don't go silent —
        # return the collected evidence digest to the user and end the session,
        # mirroring the DISPATCH-03 clean-handoff pattern. Remove once compression
        # + decision are wired.
        ctx.logger.warning(
            "[%s] Compression agent not configured — returning evidence digest to user (fallback)",
            AGENT_NAME,
        )
        if state.requester_address and CHAT_PROTOCOL_AVAILABLE:
            await ctx.send(state.requester_address, ChatMessage(
                content=[TextContent(text=_format_evidence_digest(state))]
            ))
            await ctx.send(state.requester_address, ChatMessage(content=[EndSessionContent()]))
        analysis_state.pop(request_id, None)   # guard: no stale state -> no hang


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
            # Send acknowledgement FIRST — required by Chat Protocol spec (SAFETY-03 ordering)
            await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

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

            # Process natural language question via Phase 2 router (SAFETY-03)
            ctx.logger.info(f"[{AGENT_NAME}] Processing natural language question via router")

            # Call route() OFF the event loop with a timeout; heuristic fallback on any error.
            # ACK is already sent above — do NOT reorder (SAFETY-03 ordering).
            try:
                decision = await asyncio.wait_for(
                    asyncio.to_thread(router_route, user_text),
                    timeout=ROUTER_TIMEOUT,
                )
                ctx.logger.info(
                    "[%s] route tier=%s category=%s conf=%.2f",
                    AGENT_NAME, decision.tier, decision.category, decision.confidence,
                )
            except Exception as exc:   # asyncio.TimeoutError is a subclass — caught here
                ctx.logger.warning(
                    "[%s] router error/timeout (%s) — heuristic fallback",
                    AGENT_NAME, type(exc).__name__,
                )
                decision = _heuristic_fallback(user_text)

            # Send routing note to user (DISPATCH-04): rationale + tier are both visible
            routing_note = _format_routing_note(decision)
            await ctx.send(sender, ChatMessage(
                content=[TextContent(
                    text=f"🔍 **Analyzing your question**\n\nQuestion: {user_text}\n\n{routing_note}\n\nGathering evidence from specialized agents..."
                )]
            ))

            # DISPATCH-01: map RouterDecision onto existing MarketRequest fields (no protocol change)
            market_request = _build_market_request_from_decision(user_text, decision)

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

    @chat_protocol.on_message(model=ChatAcknowledgement)
    async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        """Handle ACK receipts from users (required for protocol spec verification)."""
        ctx.logger.info(
            "[%s] ACK from %s for msg %s", AGENT_NAME, sender, msg.acknowledged_msg_id
        )


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

    # LLM availability log (SAFETY-03 no-leak: log presence/absence string, NEVER the key value)
    llm_enabled = bool(os.getenv("ASI1_API_KEY", "").strip())
    ctx.logger.info(
        "[%s] LLM %s", AGENT_NAME,
        "ENABLED (ASI1_API_KEY present)" if llm_enabled
        else "DISABLED (no ASI1_API_KEY — heuristic tier only)",
    )

    # TODO: In production, these would be loaded from environment or discovery
    ctx.logger.info("Note: Configure agent addresses via environment variables or Agentverse discovery")


if __name__ == "__main__":
    agent.run()
