"""
Standalone Decision Agent - Makes YES/NO/HOLD decisions based on intelligent compression output.

FULLY SELF-CONTAINED for Agentverse deployment (no external app/* imports).

This agent:
1. Receives compressed data from intelligent_compression_agent.py (JSON or text format)
2. Parses and analyzes the evidence facts structure
3. Calculates YES vs NO scores from supporting/contradicting facts
4. Makes a trading decision: YES, NO, or HOLD
5. Provides confidence level and detailed reasoning

Input format (from intelligent_compression_agent.py):
- JSON: {"market": {...}, "facts": [...], "summary": {...}}
  - Facts with "relation_to_market": "supports" = YES evidence
  - Facts with "relation_to_market": "contradicts" = NO evidence
- Text: "Q: question?\nYES: fact1(score)|fact2\nNO: fact3(score)"

Legacy support (from graph_compression_agent.py):
- JSON: {"nodes": [...], "edges": [...]}
- Text: "YES:claim1(score)|claim2 NO:claim3(score)"

Decision-making approach:
- Analyzes fact confidence scores weighted by relation strength
- Uses Claude for enhanced reasoning (if available)
- Falls back to score-based heuristics
- Outputs simple YES/NO/HOLD decision with confidence
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
# Use the same import as sports_video_agent
try:
    from uagents_core.contrib.protocols.chat import (
        ChatMessage,
        ChatAcknowledgement,
        TextContent,
        chat_protocol_spec,
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
    resolution_criteria: str = ""

    # Current market state
    current_yes_price: float = Field(..., ge=0.0, le=1.0)
    current_no_price: float = Field(..., ge=0.0, le=1.0)

    # Graph compression output from graph_compression_agent.py
    # Can be either:
    # 1. JSON string with {"nodes": [...], "edges": [...]}
    # 2. Text string with "YES:claim1(score)|claim2 NO:claim3(score)"
    graph_data: str

    # User constraints
    max_position_size: Optional[float] = 100.0  # Max $ to trade
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = "moderate"


class TradingDecision(BaseModel):
    """Decision output from Decision Agent"""
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    market_id: str

    # Core decision - simplified to YES/NO/HOLD
    action: Literal["YES", "NO", "HOLD"]
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Reasoning
    reasoning: str

    # Analysis from graph
    yes_score: float = Field(..., ge=0.0, le=1.0)  # Aggregate YES evidence score
    no_score: float = Field(..., ge=0.0, le=1.0)   # Aggregate NO evidence score
    yes_count: int  # Number of YES nodes
    no_count: int   # Number of NO nodes

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
            print("[DecisionEngine] No ANTHROPIC_API_KEY, using graph-based reasoning")

    def make_decision(self, request: TradingDecisionRequest) -> TradingDecision:
        """Make a trading decision based on graph compression output"""
        # Parse graph data (JSON or text format)
        graph_analysis = self._parse_graph_data(request.graph_data)

        if self.client:
            return self._make_decision_with_claude(request, graph_analysis)
        else:
            return self._make_decision_from_graph(request, graph_analysis)

    def _parse_graph_data(self, graph_data: str) -> Dict[str, Any]:
        """Parse graph data from intelligent_compression_agent.py output"""
        try:
            # Try parsing as JSON first
            data = json.loads(graph_data)

            # Check if it's intelligent_compression_agent format
            if "facts" in data and "market" in data:
                return self._analyze_intelligent_compression(data)

            # Legacy format: graph_compression_agent (if needed)
            if "nodes" in data and "edges" in data:
                return self._analyze_graph_compression(data)
        except json.JSONDecodeError:
            pass

        # Parse as text format: "Q: question?\nYES:claim1(score)|claim2 NO:claim3(score)"
        return self._analyze_text_format(graph_data)

    def _analyze_intelligent_compression(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze JSON format from intelligent_compression_agent.py"""
        facts = data.get("facts", [])
        summary = data.get("summary", {})

        # Separate facts by relation_to_market
        yes_facts = [f for f in facts if f.get("relation_to_market") == "supports"]
        no_facts = [f for f in facts if f.get("relation_to_market") == "contradicts"]

        # Calculate weighted average scores using confidence * relation_strength
        if yes_facts:
            yes_score = sum(
                f.get("confidence", 0.5) * f.get("relation_strength", 0.5)
                for f in yes_facts
            ) / len(yes_facts)
        else:
            yes_score = 0.0

        if no_facts:
            no_score = sum(
                f.get("confidence", 0.5) * f.get("relation_strength", 0.5)
                for f in no_facts
            ) / len(no_facts)
        else:
            no_score = 0.0

        # Normalize to 0-1 range
        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total
        else:
            # No facts at all - default to equal
            yes_score = 0.5
            no_score = 0.5

        return {
            "yes_nodes": yes_facts,
            "no_nodes": no_facts,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_facts),
            "no_count": len(no_facts),
            "reinforcements": 0,  # Not applicable for intelligent compression
            "contradictions": 0,   # Not applicable for intelligent compression
            "edges": [],
            "summary": summary
        }

    def _analyze_graph_compression(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze JSON graph format from graph_compression_agent (legacy)"""
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        yes_nodes = [n for n in nodes if n.get("dir") == "Y"]
        no_nodes = [n for n in nodes if n.get("dir") == "N"]

        # Calculate weighted scores
        yes_score = sum(n.get("score", 0) for n in yes_nodes) / max(len(yes_nodes), 1)
        no_score = sum(n.get("score", 0) for n in no_nodes) / max(len(no_nodes), 1)

        # Normalize to 0-1 range
        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total

        # Count reinforcement edges
        reinforcements = sum(1 for e in edges if e.get("type") == "reinforces")
        contradictions = sum(1 for e in edges if e.get("type") == "contradicts")

        return {
            "yes_nodes": yes_nodes,
            "no_nodes": no_nodes,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_nodes),
            "no_count": len(no_nodes),
            "reinforcements": reinforcements,
            "contradictions": contradictions,
            "edges": edges
        }

    def _analyze_text_format(self, text: str) -> Dict[str, Any]:
        """Analyze text format from intelligent_compression_agent.py"""
        # Format: "Q: question?\nYES: fact1(score)|fact2(score)\nNO: fact3(score)|fact4(score)"

        # Extract YES and NO sections
        yes_pattern = r'YES:\s*(.*?)(?:NO:|$)'
        no_pattern = r'NO:\s*(.*?)$'

        yes_match = re.search(yes_pattern, text, re.DOTALL)
        no_match = re.search(no_pattern, text, re.DOTALL)

        yes_nodes = []
        no_nodes = []

        if yes_match:
            yes_text = yes_match.group(1).strip()
            # Parse facts: "fact1(0.85)|fact2(0.72)"
            yes_facts = yes_text.split("|")
            for fact in yes_facts:
                if not fact.strip():
                    continue
                score_match = re.search(r'\(([0-9.]+)\)', fact)
                score = float(score_match.group(1)) if score_match else 0.5
                text_part = re.sub(r'\([0-9.]+\)', '', fact).strip()
                yes_nodes.append({
                    "text": text_part,
                    "confidence": score,
                    "relation_to_market": "supports"
                })

        if no_match:
            no_text = no_match.group(1).strip()
            no_facts = no_text.split("|")
            for fact in no_facts:
                if not fact.strip():
                    continue
                score_match = re.search(r'\(([0-9.]+)\)', fact)
                score = float(score_match.group(1)) if score_match else 0.5
                text_part = re.sub(r'\([0-9.]+\)', '', fact).strip()
                no_nodes.append({
                    "text": text_part,
                    "confidence": score,
                    "relation_to_market": "contradicts"
                })

        # Calculate weighted scores
        yes_score = sum(n["confidence"] for n in yes_nodes) / max(len(yes_nodes), 1)
        no_score = sum(n["confidence"] for n in no_nodes) / max(len(no_nodes), 1)

        # Normalize
        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total

        return {
            "yes_nodes": yes_nodes,
            "no_nodes": no_nodes,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_nodes),
            "no_count": len(no_nodes),
            "reinforcements": 0,
            "contradictions": 0,
            "edges": []
        }

    def _make_decision_with_claude(self, request: TradingDecisionRequest, graph_analysis: Dict[str, Any]) -> TradingDecision:
        """Make decision using Claude reasoning with graph analysis"""
        prompt = self._build_decision_prompt(request, graph_analysis)

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
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
                reasoning=data.get("reasoning", ""),
                yes_score=graph_analysis["yes_score"],
                no_score=graph_analysis["no_score"],
                yes_count=graph_analysis["yes_count"],
                no_count=graph_analysis["no_count"]
            )

            return decision

        except Exception as e:
            print(f"[DecisionEngine] Claude decision failed: {e}, using graph-based decision")
            return self._make_decision_from_graph(request, graph_analysis)

    def _make_decision_from_graph(self, request: TradingDecisionRequest, graph_analysis: Dict[str, Any]) -> TradingDecision:
        """Make decision based on graph analysis"""
        yes_score = graph_analysis["yes_score"]
        no_score = graph_analysis["no_score"]
        yes_count = graph_analysis["yes_count"]
        no_count = graph_analysis["no_count"]

        # Decision thresholds
        CONFIDENCE_THRESHOLD = 0.15  # Minimum difference to make a decision

        # Calculate score difference
        score_diff = yes_score - no_score

        # Make decision
        if abs(score_diff) < CONFIDENCE_THRESHOLD:
            action = "HOLD"
            confidence = 0.5
            reasoning = f"Insufficient evidence difference. YES score: {yes_score:.2f}, NO score: {no_score:.2f}. Difference ({abs(score_diff):.2f}) is below threshold ({CONFIDENCE_THRESHOLD})."
        elif score_diff > 0:
            action = "YES"
            confidence = min(0.5 + score_diff, 0.95)
            reasoning = f"YES decision based on stronger evidence. YES score: {yes_score:.2f} from {yes_count} nodes, NO score: {no_score:.2f} from {no_count} nodes."
        else:
            action = "NO"
            confidence = min(0.5 + abs(score_diff), 0.95)
            reasoning = f"NO decision based on stronger evidence. NO score: {no_score:.2f} from {no_count} nodes, YES score: {yes_score:.2f} from {yes_count} nodes."

        # Add graph edge information if available
        if graph_analysis.get("reinforcements", 0) > 0:
            reasoning += f" {graph_analysis['reinforcements']} reinforcing relationships found."
        if graph_analysis.get("contradictions", 0) > 0:
            reasoning += f" {graph_analysis['contradictions']} contradictions detected."

        # Add details about key evidence
        yes_nodes = graph_analysis.get("yes_nodes", [])
        no_nodes = graph_analysis.get("no_nodes", [])

        if yes_nodes:
            # Sort by confidence (for intelligent compression) or score (for graph compression)
            top_yes = sorted(
                yes_nodes,
                key=lambda n: n.get("confidence", n.get("score", 0)),
                reverse=True
            )[:3]
            reasoning += f"\n\nTop YES evidence:\n"
            for i, node in enumerate(top_yes, 1):
                text = node.get('text', 'N/A')[:100]
                conf = node.get("confidence", node.get("score", 0))
                reasoning += f"{i}. {text} (confidence: {conf:.2f})\n"

        if no_nodes:
            # Sort by confidence (for intelligent compression) or score (for graph compression)
            top_no = sorted(
                no_nodes,
                key=lambda n: n.get("confidence", n.get("score", 0)),
                reverse=True
            )[:3]
            reasoning += f"\nTop NO evidence:\n"
            for i, node in enumerate(top_no, 1):
                text = node.get('text', 'N/A')[:100]
                conf = node.get("confidence", node.get("score", 0))
                reasoning += f"{i}. {text} (confidence: {conf:.2f})\n"

        decision = TradingDecision(
            request_id=request.request_id,
            market_id=request.market_id,
            action=action,
            confidence=confidence,
            reasoning=reasoning.strip(),
            yes_score=yes_score,
            no_score=no_score,
            yes_count=yes_count,
            no_count=no_count
        )

        return decision

    def _build_decision_prompt(self, request: TradingDecisionRequest, graph_analysis: Dict[str, Any]) -> str:
        """Build Claude prompt for decision making"""
        yes_nodes = graph_analysis.get("yes_nodes", [])
        no_nodes = graph_analysis.get("no_nodes", [])

        # Format YES evidence - handle both intelligent compression and graph compression formats
        yes_evidence = ""
        if yes_nodes:
            yes_evidence = "\n".join([
                f"- {node.get('text', 'N/A')} (confidence: {node.get('confidence', node.get('score', 0)):.2f})"
                for node in sorted(
                    yes_nodes,
                    key=lambda n: n.get("confidence", n.get("score", 0)),
                    reverse=True
                )[:5]
            ])
        else:
            yes_evidence = "(No YES evidence)"

        # Format NO evidence
        no_evidence = ""
        if no_nodes:
            no_evidence = "\n".join([
                f"- {node.get('text', 'N/A')} (confidence: {node.get('confidence', node.get('score', 0)):.2f})"
                for node in sorted(
                    no_nodes,
                    key=lambda n: n.get("confidence", n.get("score", 0)),
                    reverse=True
                )[:5]
            ])
        else:
            no_evidence = "(No NO evidence)"

        return f"""You are a prediction market analyst. Analyze the evidence graph and make a trading decision.

MARKET QUESTION:
{request.market_question}

RESOLUTION CRITERIA:
{request.resolution_criteria or "Not specified"}

CURRENT MARKET PRICE:
YES = {request.current_yes_price:.2f} ({request.current_yes_price:.0%})
NO = {request.current_no_price:.2f} ({request.current_no_price:.0%})

GRAPH ANALYSIS:
- YES Evidence Nodes: {graph_analysis['yes_count']}
- NO Evidence Nodes: {graph_analysis['no_count']}
- YES Aggregate Score: {graph_analysis['yes_score']:.2f}
- NO Aggregate Score: {graph_analysis['no_score']:.2f}
- Reinforcing Relationships: {graph_analysis.get('reinforcements', 0)}
- Contradictions: {graph_analysis.get('contradictions', 0)}

TOP YES EVIDENCE:
{yes_evidence}

TOP NO EVIDENCE:
{no_evidence}

TASK:
Based on the graph evidence, make a decision: YES, NO, or HOLD.
Return valid JSON ONLY:

{{
  "action": "YES" | "NO" | "HOLD",
  "confidence": 0.0,
  "reasoning": "..."
}}

GUIDELINES:
1. Action should be YES if YES evidence significantly outweighs NO evidence
2. Action should be NO if NO evidence significantly outweighs YES evidence
3. Action should be HOLD if evidence is balanced or insufficient
4. Confidence (0-1): How confident are you based on evidence quality and quantity?
5. Reasoning: Explain your decision based on the evidence scores, node counts, and relationships

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

# ASI:One chat protocol (if available) - match sports_video_agent pattern
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol(spec=chat_protocol_spec)


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
        ctx.logger.info(f"  YES Score: {decision.yes_score:.2f}")
        ctx.logger.info(f"  NO Score: {decision.no_score:.2f}")
        ctx.logger.info(f"  YES Count: {decision.yes_count}")
        ctx.logger.info(f"  NO Count: {decision.no_count}")

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
    @chat_protocol.on_message(ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """Handle chat messages from DeltaV or other ASI:One compatible clients"""
        ctx.logger.info(f"[{AGENT_NAME}] Received chat message from {sender}")

        # ACK FIRST — required by Chat Protocol spec
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

        # Extract text from message using .text() method
        try:
            user_text = msg.text()
        except Exception:
            user_text = ""

        # Strip @mentions
        user_text = re.sub(r'^@[\w-]+\s+', '', user_text.strip())
        user_text = user_text.strip()

        ctx.logger.info(f"[{AGENT_NAME}] Message: {user_text[:100]}...")

        # Try to parse as JSON (structured request)
        try:
            request_data = json.loads(user_text)

            # Check if it's raw graph data (just nodes/edges or facts/market) without wrapper
            if ("nodes" in request_data or "facts" in request_data) and "market_question" not in request_data:
                # User sent raw graph data without wrapper - use defaults
                ctx.logger.info(f"[{AGENT_NAME}] Received raw graph data, using defaults")
                decision_request = TradingDecisionRequest(
                    market_id="chat-market",
                    market_question="Market analysis request",
                    resolution_criteria="",
                    current_yes_price=0.50,  # Default to 50/50 market
                    current_no_price=0.50,
                    graph_data=json.dumps(request_data),  # Re-stringify the graph
                    max_position_size=100.0,
                    risk_tolerance="moderate",
                )
            else:
                # Full request with all required fields
                decision_request = TradingDecisionRequest(
                    market_id=request_data.get("market_id", "chat-market"),
                    market_question=request_data["market_question"],
                    resolution_criteria=request_data.get("resolution_criteria", ""),
                    current_yes_price=request_data["current_yes_price"],
                    current_no_price=request_data["current_no_price"],
                    graph_data=request_data["graph_data"],
                    max_position_size=request_data.get("max_position_size", 100.0),
                    risk_tolerance=request_data.get("risk_tolerance", "moderate"),
                )

            # Make decision
            decision = decision_engine.make_decision(decision_request)

            # Format response
            response_text = f"""**Trading Decision for: {decision_request.market_question}**

**Decision**: {decision.action}
**Confidence**: {decision.confidence:.1%}

**Graph Analysis**:
- YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)
- NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)

**Reasoning**:
{decision.reasoning}
"""

            response_msg = ChatMessage(
                content=[TextContent(text=response_text)]
            )
            await ctx.send(sender, response_msg)

        except json.JSONDecodeError:
            # Check if it's a test/demo request
            user_lower = user_text.lower().strip()

            if user_lower in ["test", "demo", "example", "sample"]:
                # Run a demo decision with sample graph data
                ctx.logger.info(f"[{AGENT_NAME}] Running demo decision")

                # Sample graph data (JSON format from graph_compression_agent)
                sample_graph = json.dumps({
                    "nodes": [
                        {"id": "1", "source": "sports_video_agent", "text": "France defeated Brazil 2-1. Mbappe scored twice", "dir": "Y", "score": 0.85, "merged": 0},
                        {"id": "2", "source": "odds_agent", "text": "Betting odds favor France at 62% implied probability", "dir": "Y", "score": 0.72, "merged": 0},
                        {"id": "3", "source": "injury_agent", "text": "Kante questionable with ankle injury", "dir": "N", "score": 0.68, "merged": 0}
                    ],
                    "edges": [
                        {"from": "1", "to": "2", "type": "reinforces", "strength": 0.7}
                    ]
                })

                decision_request = TradingDecisionRequest(
                    market_id="demo-market",
                    market_question="Will France win the World Cup 2026?",
                    resolution_criteria="Resolves YES if France wins the 2026 FIFA World Cup",
                    current_yes_price=0.52,
                    current_no_price=0.48,
                    graph_data=sample_graph,
                    max_position_size=100.0,
                    risk_tolerance="moderate",
                )

                # Make decision
                decision = decision_engine.make_decision(decision_request)

                # Format detailed response
                response_text = f"""**Demo Decision Complete**

**Market Question:** Will France win the World Cup 2026?

**Input Data:**
- Current YES price: ${decision_request.current_yes_price:.2f} (52%)
- Current NO price: ${decision_request.current_no_price:.2f} (48%)

---

**DECISION: {decision.action}**

**Confidence:** {decision.confidence:.1%}

**Graph Analysis:**
- YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)
- NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)

**Reasoning:**
{decision.reasoning}

---

**To test with your own data, send JSON:**
```json
{{
  "market_question": "Your question",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "<JSON or text output from graph_compression_agent>",
  "risk_tolerance": "moderate"
}}
```
"""

                response_msg = ChatMessage(
                    content=[TextContent(text=response_text)]
                )
                await ctx.send(sender, response_msg)

            else:
                # Not JSON and not demo - provide help message
                help_message = """**Decision Agent**

I make YES/NO/HOLD decisions based on graph compression output from graph_compression_agent.

**Quick Test:**
Type 'demo' to see a sample decision!

**How to use:**

Send JSON with:
```json
{
  "market_question": "Will France win the World Cup?",
  "resolution_criteria": "Resolves YES if...",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "<output from graph_compression_agent>",
  "risk_tolerance": "moderate"
}
```

**Required fields:**
- `market_question`: The question being analyzed
- `current_yes_price`: Current YES market price (0.0-1.0)
- `current_no_price`: Current NO market price (0.0-1.0)
- `graph_data`: Graph JSON or text from graph_compression_agent

**What I return:**
- **Action**: YES, NO, or HOLD
- **Confidence**: 0.0-1.0 confidence level
- **YES/NO scores**: Aggregate evidence scores from graph
- **Reasoning**: Detailed explanation with top evidence

**Decision Process:**
1. Parse graph data (JSON or text format)
2. Analyze YES vs NO evidence scores
3. Make decision based on score difference
4. Provide confidence level and reasoning

Type 'demo' to see an example!
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

    @chat_protocol.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        """Handle acknowledgement messages"""
        ctx.logger.info(f"[{AGENT_NAME}] ACK from {sender} for msg {msg.acknowledged_msg_id}")


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
