"""
Local Chat Protocol probe for orchestrator_agent (Phase 3 routing/dispatch check).

What it verifies (depends only on the orchestrator running):
  - The orchestrator ACKs the chat message (SAFETY-03 ack-before-route).
  - It replies with a routing note that names the category, tier, confidence,
    and rationale (DISPATCH-04).
  - For a SPORTS question it dispatches to exactly one agent (watch the
    orchestrator's OWN terminal for "pending_agents = 1" / a single ctx.send).
  - For a POLITICS/finance/unknown question with no wired agent it replies
    "no live agent wired yet" and ends the session (DISPATCH-03).

Run procedure:
  Terminal A:  PYTHONPATH="$PWD:$PWD/uagents_deploy" python uagents_deploy/orchestrator_agent.py
               (note the printed agent1q… address — its routing logs are the real evidence)
  Terminal B:  PYTHONPATH="$PWD:$PWD/uagents_deploy" python uagents_deploy/send_test_orchestrator.py "Will Argentina win the World Cup 2026?"

The client prints every reply and exits on EndSession or after a timeout.
"""

import os
import sys

from uagents import Agent, Context

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    EndSessionContent,
)

# ---------------------------------------------------------------------------
# Target: the orchestrator. Prefer env var, else import the agent for its address.
# ---------------------------------------------------------------------------
TARGET_ADDRESS = os.getenv("ORCHESTRATOR_AGENT_ADDRESS")
if not TARGET_ADDRESS:
    import orchestrator_agent  # noqa: F401 — side-effect import for address
    TARGET_ADDRESS = orchestrator_agent.agent.address

# Question: first CLI arg, else a default sports question (full happy path).
QUESTION = sys.argv[1] if len(sys.argv) > 1 else "Will Argentina win the World Cup 2026?"

# Safety net: exit after this many seconds even if no EndSession arrives.
TIMEOUT_S = float(os.getenv("PROBE_TIMEOUT", "30"))

client = Agent(
    name="orchestrator_test_client",
    seed="quorum-orchestrator-test-client-v1",
    port=8105,
    mailbox=False,
)


@client.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[probe] client address: {client.address}")
    ctx.logger.info(f"[probe] sending to orchestrator {TARGET_ADDRESS}")
    ctx.logger.info(f"[probe] question: {QUESTION!r}")
    await ctx.send(TARGET_ADDRESS, ChatMessage(content=[TextContent(text=QUESTION)]))


@client.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"[probe] GOT ACK — acknowledged_msg_id={msg.acknowledged_msg_id}")


@client.on_message(ChatMessage)
async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"[probe] GOT REPLY from {sender}")
    ctx.logger.info("[probe] --- reply text ---\n" + (msg.text() or "<no text content>"))

    # Did the orchestrator end the session? (unwired handoff or final analysis)
    ended = any(isinstance(c, EndSessionContent) for c in msg.content)
    if ended:
        ctx.logger.info("[probe] session ended by orchestrator — done.")
        os._exit(0)


@client.on_interval(period=TIMEOUT_S)
async def timeout(ctx: Context):
    ctx.logger.info(f"[probe] no EndSession within {TIMEOUT_S}s — exiting (replies above are the result).")
    os._exit(0)


if __name__ == "__main__":
    client.run()
