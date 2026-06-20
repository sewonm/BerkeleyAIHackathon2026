"""
Fetch AI / Agentverse wrapper for SignalForge.

Wraps the FastAPI /analyze-market endpoint as an Agent Chat Protocol (ACP)
agent so it can be discovered and queried via ASI:One / Agentverse.

SETUP:
  pip install uagents uagents-core

DOCS TO CHECK:
  FastAPI adapter: https://docs.agentverse.ai/documentation/launch-agents/external-agents/fast-api
  ACP overview:    https://docs.agentverse.ai/documentation/launch-agents/external-agents/adapters-overview
  ASI:One ACP:     https://docs.asi1.ai/documentation/tutorials/agent-chat-protocol

HOW TO DEPLOY:
  1. Run your FastAPI backend on a publicly reachable URL (e.g. via ngrok for demo)
  2. Register this agent on Agentverse:
     https://agentverse.ai → Create Agent → External → FastAPI
  3. Paste your public URL and ACP endpoint
  4. Agent becomes discoverable on ASI:One search

ENV VARS REQUIRED:
  AGENT_SEED         (any random string, keeps agent address stable)
  BACKEND_URL        (your FastAPI URL, e.g. https://your-ngrok-url.ngrok.io)
"""

import os
import json
import httpx
from uagents import Agent, Context, Model

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AGENT_SEED = os.getenv("AGENT_SEED", "signalforge-market-research-agent-seed")


# --- ACP Message Models ---
# CHECK DOCS: exact field names may vary — verify at docs.asi1.ai

class MarketResearchRequest(Model):
    """Incoming ACP message: user asks about a prediction market."""
    market_question: str
    market_price: float
    sport: str = "soccer"


class MarketResearchResponse(Model):
    """Outgoing ACP message: compressed evidence + recommendation."""
    recommendation: str          # YES / NO / HOLD
    estimated_probability: float
    market_probability: float
    edge: float
    confidence: str
    compression_ratio: str
    reasoning: list[str]
    disclaimer: str


# --- Agent Setup ---

agent = Agent(
    name="SignalForge Market Research Agent",
    seed=AGENT_SEED,
)


@agent.on_message(model=MarketResearchRequest, replies={MarketResearchResponse})
async def handle_market_query(ctx: Context, sender: str, msg: MarketResearchRequest):
    """
    Receives a market question via ACP, calls the FastAPI backend,
    and returns the compressed recommendation.
    """
    ctx.logger.info(f"Received market query from {sender}: {msg.market_question}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/analyze-market",
                json={
                    "market_question": msg.market_question,
                    "market_price": msg.market_price,
                    "sport": msg.sport,
                }
            )
            data = response.json()

        decision = data.get("decision", {})
        metrics = data.get("compression_metrics", {})

        reply = MarketResearchResponse(
            recommendation=decision.get("recommendation", "HOLD"),
            estimated_probability=decision.get("estimated_probability", 0.5),
            market_probability=decision.get("market_probability", msg.market_price),
            edge=decision.get("edge", 0.0),
            confidence=decision.get("confidence", "low"),
            compression_ratio=metrics.get("compression_ratio", "N/A"),
            reasoning=decision.get("reasoning", []),
            disclaimer=decision.get("disclaimer", "Simulated research tool. Not financial advice.")
        )

    except Exception as e:
        ctx.logger.error(f"Backend call failed: {e}")
        reply = MarketResearchResponse(
            recommendation="HOLD",
            estimated_probability=msg.market_price,
            market_probability=msg.market_price,
            edge=0.0,
            confidence="low",
            compression_ratio="N/A",
            reasoning=[f"Research pipeline error: {str(e)}"],
            disclaimer="Simulated research tool. Not financial advice."
        )

    await ctx.send(sender, reply)


if __name__ == "__main__":
    print(f"Agent address: {agent.address}")
    print(f"Connecting to backend: {BACKEND_URL}")
    agent.run()
