"""
Sends a real EvidenceRequest to the deployed culture_web_agent on Agentverse
and prints the response. Run this to confirm the agent is alive and returning
real chunks before handing the address to the orchestrator.

Usage:
    python test_culture_agent_live.py ["market question"]

Reads CULTURE_WEB_AGENT_ADDRESS from .env (or environment).
"""

import sys
import os
import threading
from uuid import uuid4
from typing import Optional, List, Literal
from uuid import UUID

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from uagents import Agent, Context, Protocol

load_dotenv()

CULTURE_AGENT_ADDRESS = os.getenv("CULTURE_WEB_AGENT_ADDRESS")
if not CULTURE_AGENT_ADDRESS:
    print("Error: CULTURE_WEB_AGENT_ADDRESS not set in .env")
    sys.exit(1)

MARKET_QUESTION = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Will the S&P 500 close above 6000 by end of 2025?"

# ---------------------------------------------------------------------------
# Shared message models (must match the deployed agent exactly)
# ---------------------------------------------------------------------------

class EvidenceRequest(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    market_question: str
    market_id: Optional[str] = None
    category: str
    protected_terms: List[str] = Field(default_factory=list)


class EvidenceChunkMsg(BaseModel):
    source_type: Literal[
        "culture_web", "sports_video", "politics_news",
        "financial_research", "market", "manual"
    ]
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: dict = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    agent_name: str
    evidence_chunks: List[EvidenceChunkMsg]
    total_chunks: int


class AgentStatus(BaseModel):
    msg_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    status: Literal["ready", "processing", "completed", "error"]
    message: str

# ---------------------------------------------------------------------------
# Test agent
# ---------------------------------------------------------------------------

tester = Agent(
    name="culture_tester",
    seed="culture_tester_local_seed_ephemeral",
    port=8099,
)

proto = Protocol("EvidenceCollection")


@tester.on_event("startup")
async def on_start(ctx: Context):
    print(f"\nTester address: {ctx.agent.address}")
    print(f"Sending request to: {CULTURE_AGENT_ADDRESS}")
    print(f"Question: {MARKET_QUESTION}\n")

    await ctx.send(CULTURE_AGENT_ADDRESS, EvidenceRequest(
        market_question=MARKET_QUESTION,
        market_id="TEST-001",
        category="culture",
    ))

    print("Request sent. Check Agentverse logs for your culture agent.")
    print("You should see: processing → completed with N chunks\n")
    threading.Timer(2, lambda: os._exit(0)).start()


@proto.on_message(model=AgentStatus)
async def on_status(ctx: Context, sender: str, msg: AgentStatus):
    print(f"[STATUS] {msg.status.upper()}: {msg.message}")
    if msg.status == "error":
        print("\nAgent returned an error — check Agentverse logs.")
        await ctx.stop()


@proto.on_message(model=EvidenceResponse)
async def on_response(ctx: Context, sender: str, msg: EvidenceResponse):
    print(f"\nReceived {msg.total_chunks} chunks from {msg.agent_name}\n")
    print("=" * 60)

    for i, chunk in enumerate(msg.evidence_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"URL:        {chunk.source_url}")
        print(f"Confidence: {chunk.confidence}")
        print(f"Mock:       {chunk.metadata.get('mock')}")
        print()
        print(chunk.text[:600])
        print()

    if msg.total_chunks == 0:
        print("WARNING: got 0 chunks — agent ran but produced no evidence.")
    elif msg.evidence_chunks[0].metadata.get("mock"):
        print("WARNING: chunks are mock data — BROWSERBASE_API_KEY may not be set in Agentverse.")
    else:
        print("OK: live evidence chunks received.")

    await ctx.stop()


tester.include(proto)

if __name__ == "__main__":
    tester.run()