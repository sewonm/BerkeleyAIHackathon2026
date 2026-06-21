"""
DecisionAgent - Standalone uAgent for making trading decisions.

This agent receives compressed evidence and makes YES/NO/HOLD recommendations
with confidence scores and reasoning.

Deployable to Agentverse as an independent service.
"""

from uagents import Agent, Context, Protocol
from protocols.messages import (
    DecisionRequest,
    DecisionResponse,
    AgentStatus
)

# Import decision logic from main app
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.agents.decision_agent import DecisionAgent as DecisionLogic
from app.schemas.market import Market

# Agent configuration
AGENT_NAME = "decision_agent"
AGENT_SEED = "decision_agent_seed_phrase_change_in_production"
AGENT_PORT = 8003
AGENT_MAILBOX = True

# Create the agent
agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

# Create protocol
decision_protocol = Protocol("TradingDecision")

# Initialize decision logic
decision_logic = DecisionLogic()


@decision_protocol.on_message(model=DecisionRequest)
async def handle_decision_request(ctx: Context, sender: str, msg: DecisionRequest):
    """
    Handle decision requests.

    Args:
        ctx: Agent context
        sender: Address of requesting agent
        msg: Decision request message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received decision request from {sender}")
    ctx.logger.info(f"Market: {msg.market_title}")
    ctx.logger.info(f"Current YES price: {msg.current_yes_price}")

    # Send processing status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Analyzing compressed evidence for decision"
    ))

    # Create temporary market object
    temp_market = Market(
        market_id="temp",
        title=msg.market_title,
        question=msg.market_question,
        category="general",
        current_yes_price=msg.current_yes_price,
        resolution_criteria="N/A",
        protected_terms=[]
    )

    # Make decision using compressed context
    # For the decision agent, we need to reconstruct kept_chunks from compressed context
    # For MVP, we'll use a simplified approach
    kept_chunks = [
        {"text": msg.compressed_context, "score": 1.0}
    ]

    decision = decision_logic.run(
        market=temp_market,
        compressed_context=msg.compressed_context,
        kept_chunks=kept_chunks
    )

    ctx.logger.info(f"[{AGENT_NAME}] Decision: {decision.recommendation}")
    ctx.logger.info(f"Confidence: {decision.confidence:.2f}")

    try:
        from agent_memory_service import store_decision
        store_decision(
            market_id=msg.market_title,
            decision=decision.recommendation,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
        )
        ctx.logger.info(f"[{AGENT_NAME}] Stored decision in Agent Memory")
    except Exception as e:
        ctx.logger.warning(f"[{AGENT_NAME}] Agent Memory write skipped: {e}")

    # Send response
    response = DecisionResponse(
        request_id=msg.msg_id,
        recommendation=decision.recommendation,
        confidence=decision.confidence,
        fair_probability=decision.fair_probability,
        reasoning=decision.reasoning,
        key_evidence=decision.key_evidence,
        missing_info=decision.missing_info
    )

    await ctx.send(sender, response)

    # Send completion status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Recommendation: {decision.recommendation} ({decision.confidence:.0%} confidence)"
    ))


# Include protocol
agent.include(decision_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to make trading decisions")


if __name__ == "__main__":
    agent.run()
