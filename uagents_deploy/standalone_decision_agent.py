"""
Standalone Decision Agent - Makes trading decisions based on compressed context.

FULLY SELF-CONTAINED for Agentverse deployment (no external app/* imports).

This agent:
1. Receives compressed context from Compression Agent
2. Analyzes the evidence
3. Estimates fair value for the market
4. Makes a trading decision (BUY_YES/BUY_NO/SELL/HOLD)
5. Calculates position sizing based on edge and risk tolerance

Decision-making approach:
- Uses Claude for reasoning (if available)
- Applies Kelly Criterion for position sizing
- Considers edge, confidence, and risk tolerance
- Outputs structured decision with reasoning
"""

import os
import json
import re
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field

from uagents import Agent, Context, Protocol

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


# ============================================================================
# SCHEMAS (Self-contained)
# ============================================================================

class TradingDecisionRequest(BaseModel):
    """Request to Decision Agent for a trading decision"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    market_question: str
    resolution_criteria: str

    # Current market state
    current_yes_price: float = Field(..., ge=0.0, le=1.0)
    current_no_price: float = Field(..., ge=0.0, le=1.0)
    volume_24h: Optional[float] = None
    liquidity: Optional[float] = None

    # Compressed context from Compression Agent
    compressed_context: str
    compression_metrics: Optional[Dict[str, Any]] = None

    # Evidence summary (optional, from Compression Agent)
    top_yes_evidence: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    top_no_evidence: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    contradictions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # User constraints
    max_position_size: Optional[float] = 100.0  # Max $ to trade
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = "moderate"
    existing_position: Optional[float] = None  # Current position in market


class TradingDecision(BaseModel):
    """Decision output from Decision Agent"""
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    market_id: str

    # Core decision
    action: Literal["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO", "HOLD"]
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Position sizing
    suggested_position_size: float = Field(..., ge=0.0)  # $ amount
    suggested_contracts: Optional[int] = None

    # Pricing
    estimated_fair_value: float = Field(..., ge=0.0, le=1.0)
    price_limit: Optional[float] = None

    # Reasoning
    reasoning: str
    key_factors: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    # Expected value calculation
    expected_value: Optional[float] = None
    edge: Optional[float] = None

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)


class TradingDecisionResponse(BaseModel):
    """Response from Decision Agent"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    decision: Optional[TradingDecision] = None


# ============================================================================
# DECISION ENGINE
# ============================================================================

class DecisionEngine:
    """Core decision engine for trading"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                print("[DecisionEngine] Claude-based reasoning enabled")
            except ImportError:
                print("[DecisionEngine] anthropic package not installed")
                self.client = None
        else:
            print("[DecisionEngine] No ANTHROPIC_API_KEY, using heuristic reasoning")

    def make_decision(self, request: TradingDecisionRequest) -> TradingDecision:
        """Make a trading decision based on compressed context"""
        if self.client:
            return self._make_decision_with_claude(request)
        else:
            return self._make_decision_heuristic(request)

    def _make_decision_with_claude(self, request: TradingDecisionRequest) -> TradingDecision:
        """Make decision using Claude reasoning"""
        prompt = self._build_decision_prompt(request)

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse JSON response
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse JSON from Claude response")

            # Build decision
            decision = TradingDecision(
                request_id=request.request_id,
                market_id=request.market_id,
                action=data.get("action", "HOLD"),
                confidence=data.get("confidence", 0.5),
                suggested_position_size=data.get("suggested_position_size", 0.0),
                estimated_fair_value=data.get("estimated_fair_value", request.current_yes_price),
                price_limit=data.get("price_limit"),
                reasoning=data.get("reasoning", ""),
                key_factors=data.get("key_factors", []),
                risks=data.get("risks", []),
                expected_value=data.get("expected_value"),
                edge=data.get("edge")
            )

            return decision

        except Exception as e:
            print(f"[DecisionEngine] Claude decision failed: {e}, using heuristic")
            return self._make_decision_heuristic(request)

    def _make_decision_heuristic(self, request: TradingDecisionRequest) -> TradingDecision:
        """Make decision using heuristic approach"""
        # Parse compressed context for YES/NO evidence
        yes_count = request.compressed_context.lower().count("yes evidence")
        no_count = request.compressed_context.lower().count("no evidence")

        # Use provided evidence lists if available
        if request.top_yes_evidence:
            yes_count = len(request.top_yes_evidence)
        if request.top_no_evidence:
            no_count = len(request.top_no_evidence)

        # Calculate simple fair value estimate
        if yes_count + no_count == 0:
            estimated_fair_value = 0.5
        else:
            estimated_fair_value = yes_count / (yes_count + no_count)

        # Calculate edge
        edge = estimated_fair_value - request.current_yes_price

        # Make decision based on edge
        if abs(edge) < 0.05:
            action = "HOLD"
            confidence = 0.5
        elif edge > 0.05:
            action = "BUY_YES"
            confidence = min(0.5 + abs(edge), 0.9)
        else:
            action = "BUY_NO"
            confidence = min(0.5 + abs(edge), 0.9)

        # Position sizing using simplified Kelly
        kelly_fraction = edge * confidence if abs(edge) > 0 else 0.0
        risk_multiplier = {"conservative": 0.25, "moderate": 0.5, "aggressive": 1.0}
        multiplier = risk_multiplier.get(request.risk_tolerance or "moderate", 0.5)

        suggested_position_size = min(
            abs(kelly_fraction) * multiplier * (request.max_position_size or 100.0),
            request.max_position_size or 100.0
        )

        if action == "HOLD":
            suggested_position_size = 0.0

        # Build reasoning
        reasoning = f"""
Heuristic Decision Analysis:

YES Evidence: {yes_count} items
NO Evidence: {no_count} items

Estimated Fair Value: {estimated_fair_value:.2f}
Current YES Price: {request.current_yes_price:.2f}
Edge: {edge:+.2f}

Decision: {action}
Confidence: {confidence:.2f}
Position Size: ${suggested_position_size:.2f}

Risk Tolerance: {request.risk_tolerance or 'moderate'}
Kelly Fraction: {kelly_fraction:.3f}
Risk Multiplier: {multiplier}
        """.strip()

        decision = TradingDecision(
            request_id=request.request_id,
            market_id=request.market_id,
            action=action,
            confidence=confidence,
            suggested_position_size=suggested_position_size,
            estimated_fair_value=estimated_fair_value,
            price_limit=None,
            reasoning=reasoning,
            key_factors=[
                f"{yes_count} YES evidence items",
                f"{no_count} NO evidence items",
                f"Edge: {edge:+.2%}"
            ],
            risks=[
                "Heuristic reasoning (not Claude-based)",
                "Limited evidence analysis",
                "Simple fair value estimation"
            ],
            expected_value=None,
            edge=edge
        )

        return decision

    def _build_decision_prompt(self, request: TradingDecisionRequest) -> str:
        """Build Claude prompt for decision making"""
        return f"""You are a prediction market trading analyst. Analyze the compressed evidence and make a trading decision.

MARKET QUESTION:
{request.market_question}

RESOLUTION CRITERIA:
{request.resolution_criteria}

CURRENT MARKET PRICE:
YES = {request.current_yes_price:.2f} ({request.current_yes_price:.0%})
NO = {request.current_no_price:.2f} ({request.current_no_price:.0%})

COMPRESSED EVIDENCE CONTEXT:
{request.compressed_context}

USER CONSTRAINTS:
- Max Position Size: ${request.max_position_size or 100.0}
- Risk Tolerance: {request.risk_tolerance or 'moderate'}
- Existing Position: ${request.existing_position or 0.0}

TASK:
Analyze the evidence and make a trading decision. Return valid JSON ONLY:

{{
  "action": "BUY_YES | BUY_NO | SELL_YES | SELL_NO | HOLD",
  "confidence": 0.0,
  "suggested_position_size": 0.0,
  "estimated_fair_value": 0.0,
  "price_limit": 0.0,
  "reasoning": "...",
  "key_factors": ["...", "..."],
  "risks": ["...", "..."],
  "expected_value": 0.0,
  "edge": 0.0
}}

DECISION GUIDELINES:
1. Estimate fair value (0-1) based on the evidence
2. Calculate edge = estimated_fair_value - current_yes_price
3. Action:
   - If edge > 0.05: BUY_YES (market underpriced)
   - If edge < -0.05: BUY_NO (market overpriced)
   - If |edge| < 0.05: HOLD (fairly priced)
4. Confidence (0-1): How confident are you in your fair value estimate?
5. Position sizing: Use Kelly Criterion
   - kelly_fraction = edge * confidence
   - Adjust for risk tolerance (conservative=0.25x, moderate=0.5x, aggressive=1.0x)
   - suggested_position_size = kelly_fraction * risk_multiplier * max_position_size
6. Price limit: Max price you'd pay (for buys) or min for sells
7. Expected value: (win_prob * win_amount) - (loss_prob * loss_amount)
8. List key factors driving your decision
9. List main risks/uncertainties

Return JSON only, no other text.
"""


# ============================================================================
# UAGENT SETUP
# ============================================================================

AGENT_NAME = "decision_agent_standalone"
AGENT_SEED = "decision_agent_standalone_seed_change_in_production"
AGENT_PORT = 8003
AGENT_MAILBOX = True

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,
)

decision_protocol = Protocol("StandaloneTradingDecision")
decision_engine = DecisionEngine()

# ASI:One chat protocol (if available)
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol("Chat", spec=chat_protocol_spec)


@decision_protocol.on_message(model=TradingDecisionRequest)
async def handle_decision_request(ctx: Context, sender: str, msg: TradingDecisionRequest):
    """Handle trading decision requests"""
    ctx.logger.info(f"[{AGENT_NAME}] Received decision request from {sender}")
    ctx.logger.info(f"Market: {msg.market_question}")
    ctx.logger.info(f"Current YES price: {msg.current_yes_price:.2f}")

    try:
        # Make decision
        decision = decision_engine.make_decision(msg)

        # Send response
        response = TradingDecisionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="success",
            decision=decision
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Decision complete")
        ctx.logger.info(f"  Action: {decision.action}")
        ctx.logger.info(f"  Confidence: {decision.confidence:.2f}")
        ctx.logger.info(f"  Fair Value: {decision.estimated_fair_value:.2f}")
        ctx.logger.info(f"  Edge: {decision.edge:+.2%}" if decision.edge else "  Edge: N/A")
        ctx.logger.info(f"  Position Size: ${decision.suggested_position_size:.2f}")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Decision failed: {e}")
        import traceback
        ctx.logger.error(traceback.format_exc())

        # Send error response
        response = TradingDecisionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="error",
            error=str(e)
        )

        await ctx.send(sender, response)


# ============================================================================
# ASI:One Chat Protocol Handler (DeltaV Integration)
# ============================================================================

if CHAT_PROTOCOL_AVAILABLE:
    @chat_protocol.on_message(model=ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """Handle chat messages from DeltaV or other ASI:One compatible clients"""
        ctx.logger.info(f"[{AGENT_NAME}] Received chat message from {sender}")

        # Send acknowledgement
        await ctx.send(sender, ChatAcknowledgement())

        # Extract text from message content
        user_text = ""
        for content in msg.content:
            if isinstance(content, TextContent):
                user_text += content.text

        ctx.logger.info(f"[{AGENT_NAME}] Message: {user_text[:100]}...")

        # Try to parse as JSON (structured request)
        try:
            request_data = json.loads(user_text)

            # Build TradingDecisionRequest
            decision_request = TradingDecisionRequest(
                market_id=request_data.get("market_id", "chat-market"),
                market_question=request_data["market_question"],
                resolution_criteria=request_data["resolution_criteria"],
                current_yes_price=request_data["current_yes_price"],
                current_no_price=request_data["current_no_price"],
                compressed_context=request_data["compressed_context"],
                max_position_size=request_data.get("max_position_size", 100.0),
                risk_tolerance=request_data.get("risk_tolerance", "moderate"),
            )

            # Make decision
            decision = decision_engine.make_decision(decision_request)

            # Format response
            response_text = f"""**Trading Decision for: {decision_request.market_question}**

**Decision**: {decision.action}

**Fair Value Estimate**: {decision.estimated_fair_value:.2%}
**Current Market Price**: {decision_request.current_yes_price:.2%}
**Edge**: {decision.edge:+.2%}

**Position Sizing**:
- Suggested Position: ${decision.suggested_position_size:.2f}
- Max Position: ${decision_request.max_position_size:.2f}
- Confidence: {decision.confidence:.1%}

**Reasoning**:
{decision.reasoning}

**Risk Factors**:
{chr(10).join('- ' + r for r in decision.risk_factors)}
"""

            response_msg = ChatMessage(
                content=[TextContent(text=response_text)]
            )
            await ctx.send(sender, response_msg)

        except json.JSONDecodeError:
            # Not JSON - provide help message
            help_message = f"""**Decision Agent**

I make trading decisions based on compressed market context.

**How to use me**:

Send a JSON request with:
```json
{{
  "market_question": "Will France win the World Cup?",
  "resolution_criteria": "Resolves YES if...",
  "current_yes_price": 0.18,
  "current_no_price": 0.82,
  "compressed_context": "<compressed evidence from Compression Agent>",
  "max_position_size": 100.0,
  "risk_tolerance": "moderate"
}}
```

**Risk Tolerance Options**: "conservative", "moderate", "aggressive"

**Outputs**:
- Trading action (BUY_YES/BUY_NO/HOLD)
- Fair value estimate
- Edge calculation
- Position sizing (Kelly Criterion)
- Detailed reasoning
- Risk factors

I use Claude for reasoning (if available) with Kelly Criterion for position sizing.
"""

            response_msg = ChatMessage(
                content=[TextContent(text=help_message)]
            )
            await ctx.send(sender, response_msg)

        except Exception as e:
            # Error handling
            error_text = f"**Error**: Failed to process decision request\n\n{str(e)}"
            response_msg = ChatMessage(
                content=[TextContent(text=error_text)]
            )
            await ctx.send(sender, response_msg)
            ctx.logger.error(f"[{AGENT_NAME}] Chat handler error: {e}")

        finally:
            # Always end the session
            await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))


# ============================================================================
# Protocol Inclusion
# ============================================================================

# Include custom protocol for agent-to-agent communication
agent.include(decision_protocol, publish_manifest=False)

# Include ASI:One chat protocol if available
if CHAT_PROTOCOL_AVAILABLE:
    agent.include(chat_protocol, publish_manifest=True)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Standalone Decision Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to make trading decisions")

    # Protocol status
    ctx.logger.info("Custom protocol: ENABLED (agent-to-agent communication)")
    if CHAT_PROTOCOL_AVAILABLE:
        ctx.logger.info("ASI:One chat protocol: ENABLED (DeltaV compatible)")
    else:
        ctx.logger.info("ASI:One chat protocol: DISABLED (install uagents[chat])")

    if decision_engine.client:
        ctx.logger.info("Decision mode: Claude-based reasoning")
    else:
        ctx.logger.info("Decision mode: Heuristic reasoning")


if __name__ == "__main__":
    agent.run()
