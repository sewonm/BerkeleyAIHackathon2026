"""
SignalForge — Agentverse / ASI:One compatible agent.

This is the PUBLIC FRONT DOOR. It:
  1. Registers on Agentverse with a stable address (seed-based)
  2. Implements Agent Chat Protocol so ASI:One can find and talk to it
  3. Accepts a natural language market question as a chat message
  4. Calls our FastAPI backend to do the real work
  5. Returns a human-readable research summary

ASI:One mental model:
  ASI:One finds this agent → sends a ChatMessage → we call backend → reply with ChatMessage

INSTALL:
  pip install uagents uagents-core httpx

RUN:
  python agentverse/agent_wrapper.py

ENV VARS:
  AGENT_SEED    (string, any value — keeps agent address stable across restarts)
  BACKEND_URL   (our FastAPI URL, default http://localhost:8000)
  AGENT_PORT    (default 8001)

DEPLOY NOTE:
  For Agentverse to reach this agent, it needs a public URL.
  For demo: use ngrok → ngrok http 8001 → paste URL in Agentverse registration.
  Agentverse → Create Agent → External → uAgents → paste public URL

DOCS:
  ASI:One example: https://uagents.fetch.ai/docs/examples/asi-1
  External agent:  https://docs.agentverse.ai/documentation/launch-agents/external-agents/u-agents
  Seed/address:    https://uagents.fetch.ai/docs/getting-started/create
"""

import os
import re
import httpx
from datetime import datetime
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

# ── Config ────────────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AGENT_SEED  = os.getenv("AGENT_SEED", "signalforge-market-research-agent-v1-seed")
AGENT_PORT  = int(os.getenv("AGENT_PORT", "8001"))

# ── Agent identity ────────────────────────────────────────────────────────
# seed= is REQUIRED for a stable address. Without it, address changes every restart
# and Agentverse loses track of your agent.

agent = Agent(
    name="signalforge-market-research",
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,              # required for Agentverse discoverability
    publish_agent_details=True,
)

# ── Chat Protocol (required for ASI:One compatibility) ───────────────────

protocol = Protocol(spec=chat_protocol_spec)


@protocol.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Receives a natural language market question from ASI:One or any ACP-compatible caller.
    Calls our FastAPI backend, formats the result, sends back a ChatMessage.

    Example input text:
      "Will Brazil beat Mexico in the World Cup? The current YES price is 0.61."
      "Analyze market: Lakers vs Warriors, price 0.54, NBA"
    """
    # Step 1: acknowledge receipt immediately (required by ACP)
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Step 2: extract text from the message content
    user_text = ""
    for item in msg.content:
        if isinstance(item, TextContent):
            user_text += item.text

    ctx.logger.info(f"[signalforge] Received: {user_text[:120]}")

    # Step 3: parse market question + price from text
    parsed = _parse_market_input(user_text)

    # Step 4: call our FastAPI backend
    response_text = await _call_backend(parsed)

    # Step 5: send response back as ChatMessage
    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response_text),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    """Receive acknowledgements — no action needed."""
    pass


# ── Include protocol and run ──────────────────────────────────────────────

agent.include(protocol, publish_manifest=True)


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_market_input(text: str) -> dict:
    """
    Extracts market_question and market_price from natural language text.
    Simple heuristic — works for demo inputs. No LLM needed.

    Examples handled:
      "Will Brazil beat Mexico? Price 0.61"
      "Analyze: Lakers vs Warriors, YES price is 0.54, sport NBA"
    """
    # Extract market price — look for decimal like 0.XX or 0.X
    price_match = re.search(r"\b0\.\d{1,2}\b", text)
    market_price = float(price_match.group()) if price_match else 0.50

    # Extract sport if mentioned
    sport = "soccer"
    text_lower = text.lower()
    if any(k in text_lower for k in ["nba", "basketball", "lakers", "warriors", "celtics"]):
        sport = "basketball"
    elif any(k in text_lower for k in ["nfl", "football", "touchdown"]):
        sport = "football"
    elif any(k in text_lower for k in ["mlb", "baseball"]):
        sport = "baseball"

    # Extract teams — look for "X vs Y" or "X beat Y" pattern
    teams = []
    vs_match = re.search(r"([A-Z][a-zA-Z\s]+?)\s+(?:vs\.?|beat|versus)\s+([A-Z][a-zA-Z\s]+?)(?:\?|,|\.|$)", text)
    if vs_match:
        teams = [vs_match.group(1).strip(), vs_match.group(2).strip()]

    # Market question is the full input (trimmed)
    question = text.strip()
    if len(question) > 300:
        question = question[:300]

    return {
        "market_question": question,
        "market_price": market_price,
        "sport": sport,
        "teams": teams or ["Team A", "Team B"],
    }


async def _call_backend(parsed: dict) -> str:
    """
    Calls POST /analyze-market on our FastAPI backend.
    Returns a formatted text response for ASI:One.
    """
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/analyze-market",
                json=parsed,
            )
            response.raise_for_status()
            data = response.json()

        decision = data.get("decision", {})
        metrics  = data.get("compression_metrics", {})

        rec       = decision.get("recommendation", "HOLD")
        est_prob  = decision.get("estimated_probability", 0.5)
        mkt_prob  = decision.get("market_probability", parsed["market_price"])
        edge      = decision.get("edge", 0.0)
        confidence = decision.get("confidence", "low")
        reasoning  = decision.get("reasoning", [])
        risks      = decision.get("risks", [])
        ratio      = metrics.get("compression_ratio", "N/A")
        reduction  = metrics.get("token_reduction_pct", 0)

        lines = [
            f"SignalForge Market Research — {parsed['market_question']}",
            "",
            f"Recommendation:        {rec}",
            f"Estimated probability: {est_prob:.0%}",
            f"Market probability:    {mkt_prob:.0%}",
            f"Edge:                  {edge:+.1%}",
            f"Confidence:            {confidence}",
            "",
            f"Evidence compression:  {ratio} ({reduction}% token reduction)",
            "",
            "Key evidence:",
        ]
        for r in reasoning[:4]:
            lines.append(f"  • {r}")

        if risks:
            lines.append("")
            lines.append("Key risks:")
            for r in risks[:2]:
                lines.append(f"  • {r}")

        lines.append("")
        lines.append("Simulated research tool. Not financial advice.")

        return "\n".join(lines)

    except httpx.ConnectError:
        return (
            f"SignalForge backend is not reachable at {BACKEND_URL}.\n"
            "Make sure the FastAPI server is running and BACKEND_URL is set correctly.\n\n"
            "Simulated research tool. Not financial advice."
        )
    except Exception as e:
        return (
            f"Research pipeline error: {e}\n\n"
            "Simulated research tool. Not financial advice."
        )


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Agent name:    signalforge-market-research")
    print(f"Agent address: {agent.address}")
    print(f"Backend URL:   {BACKEND_URL}")
    print(f"Port:          {AGENT_PORT}")
    print()
    print("Copy the agent address above into your Agentverse registration.")
    print("Run ngrok to get a public URL: ngrok http 8001")
    print()
    agent.run()
