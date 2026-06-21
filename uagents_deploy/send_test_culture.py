"""
Local two-terminal Chat Protocol round-trip verifier for culture_web_agent.

Two-process run procedure:
  Terminal A:  python uagents_deploy/culture_web_agent.py
               (note the printed agent1q… address)
  Terminal B:  python uagents_deploy/send_test_culture.py

  Expect Terminal B to log:
    GOT ACK
    GOT BUNDLE REPLY  with >=2 culture_web chunks.

The client exits automatically after receiving the bundle reply (os._exit(0)).
"""

import json
import os

from uagents import Agent, Context

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
)

# ---------------------------------------------------------------------------
# Target address: prefer env var, fall back to importing the agent directly
# ---------------------------------------------------------------------------

TARGET_ADDRESS = os.getenv("CULTURE_WEB_AGENT_ADDRESS")
if not TARGET_ADDRESS:
    import culture_web_agent  # noqa: F401 — side-effect import for address
    TARGET_ADDRESS = culture_web_agent.agent.address

# ---------------------------------------------------------------------------
# Client agent — distinct seed and port, no mailbox needed for local testing
# ---------------------------------------------------------------------------

client = Agent(
    name="culture_test_client",
    seed="quorum-culture-test-client-v1",
    port=8101,
    mailbox=False,
)


@client.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[test_client] Started — address: {client.address}")
    ctx.logger.info(f"[test_client] Sending ChatMessage to {TARGET_ADDRESS}")

    await ctx.send(
        TARGET_ADDRESS,
        ChatMessage(
            content=[
                TextContent(text="Will Dune: Part Two win Best Picture at the 2026 Oscars?")
            ]
        ),
    )


@client.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(
        f"[test_client] GOT ACK — acknowledged_msg_id={msg.acknowledged_msg_id}"
    )


def _extract_bundle_json(text: str):
    """The reply is a human-readable summary + a fenced ```json bundle block."""
    if "```json" in text:
        body = text.split("```json", 1)[1].split("```", 1)[0].strip()
        return json.loads(body)
    return json.loads(text)


@client.on_message(ChatMessage)
async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
    """This is the bundle reply from culture_web_agent."""
    ctx.logger.info(f"[test_client] GOT BUNDLE REPLY from {sender}")
    ctx.logger.info("[test_client] --- reply preview ---\n" + msg.text()[:400])

    try:
        chunks = _extract_bundle_json(msg.text())
    except Exception as exc:
        ctx.logger.error(f"[test_client] Failed to parse bundle JSON: {exc}")
        os._exit(1)

    assert isinstance(chunks, list) and len(chunks) >= 2, (
        f"Expected >=2 chunks, got {len(chunks) if isinstance(chunks, list) else type(chunks)}"
    )

    for chunk in chunks:
        assert chunk.get("source_type") == "culture_web", (
            f"Unexpected source_type: {chunk.get('source_type')}"
        )

    ctx.logger.info(
        f"[test_client] Bundle verified — {len(chunks)} culture_web chunks received"
    )
    for i, chunk in enumerate(chunks):
        ctx.logger.info(f"  chunk[{i}] kind={chunk.get('metadata', {}).get('kind')} | {chunk.get('text', '')[:80]}")

    # Clean exit after successful round-trip
    os._exit(0)


if __name__ == "__main__":
    client.run()