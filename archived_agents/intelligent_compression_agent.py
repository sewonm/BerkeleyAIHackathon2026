"""
Intelligent Compression Agent - Deployed Fetch.ai uAgent

Parses rough noisy text (JSON/HTML/scraped) from research agents
Builds market-centric graph with facts pointing to market question
Achieves real compression via intelligent parsing and deduplication

DEPLOY AS MAILBOX AGENT:
    python uagents_deploy/intelligent_compression_agent.py
"""

import os
import json
import re
import asyncio
import traceback

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from uagents import Agent, Context, Protocol
from protocols.messages import (
    CompressionRequest,
    CompressionResponse,
    EvidenceChunkMsg
)
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

from intelligent_compressor import IntelligentCompressor

# ============================================================================
# AGENT SETUP
# ============================================================================

AGENT_NAME = "intelligent_compression_agent"
AGENT_SEED = os.getenv("COMPRESSION_AGENT_SEED", "intelligent-compression-agent-seed-v1")
AGENT_PORT = 8007
AGENT_MAILBOX = True
AGENT_DESCRIPTION = (
    "Intelligent Compression Agent — parses rough noisy text (JSON/HTML/scraped data) "
    "from research agents, extracts clean facts, builds market-centric graph, and "
    "achieves 3-10x compression while preserving key evidence."
)

README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "INTELLIGENT_COMPRESSION_README.md")

_agent_kwargs = dict(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
    description=AGENT_DESCRIPTION,
    publish_agent_details=True,
)
if os.path.exists(README_PATH):
    _agent_kwargs["readme_path"] = README_PATH

agent = Agent(**_agent_kwargs)

# Create compressor instance
compressor = IntelligentCompressor()


# ============================================================================
# CHAT PROTOCOL (ASI:One)
# ============================================================================

chat_protocol = Protocol(spec=chat_protocol_spec)


@chat_protocol.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle chat messages from ASI:One"""
    try:
        # ACK first
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

        # Extract text
        try:
            user_text = msg.text()
        except Exception:
            user_text = ""

        # Strip @mentions
        user_text = re.sub(r'^@[\w-]+\s+', '', user_text.strip())

        ctx.logger.info(f"[{AGENT_NAME}] Chat from {sender}: {user_text[:100]}...")

        # Try to parse as JSON request
        try:
            request_data = json.loads(user_text)

            # Build compression request
            market_question = request_data.get("market_question", "")
            protected_terms = request_data.get("protected_terms", [])
            token_budget = request_data.get("token_budget", 200)
            output_format = request_data.get("output_format", "json")

            # Convert evidence chunks
            evidence_chunks = []
            for chunk_data in request_data.get("evidence_chunks", []):
                if isinstance(chunk_data, dict):
                    evidence_chunks.append(chunk_data)

            # Compress
            compressed_output, metrics = compressor.compress(
                market_question=market_question,
                protected_terms=protected_terms,
                evidence_chunks=evidence_chunks,
                token_budget=token_budget,
                output_format=output_format
            )

            # Format response
            response_text = f"""
**Intelligent Compression Complete** 🧠🗜️

**Parsing:**
- JSON chunks parsed: {metrics['json_parses']}
- HTML chunks parsed: {metrics['html_parses']}
- Text chunks parsed: {metrics['text_parses']}

**Extraction:**
- Facts extracted: {metrics['facts_extracted']}
- After deduplication: {metrics['facts_after_dedup']}
- Final facts: {metrics['facts_final']}

**Market-Centric Analysis:**
- Supporting facts (YES): {metrics['supporting_facts']}
- Contradicting facts (NO): {metrics['contradicting_facts']}
- Neutral facts: {metrics['neutral_facts']}

**Compression:**
- Raw tokens: {metrics['raw_tokens']}
- Compressed tokens: {metrics['compressed_tokens']}
- **Compression ratio: {metrics['compression_ratio']}x** ✨

**Compressed Output:**
```
{compressed_output[:1000]}{'...' if len(compressed_output) > 1000 else ''}
```
"""

            response_msg = ChatMessage(content=[TextContent(text=response_text)])
            await ctx.send(sender, response_msg)

        except json.JSONDecodeError:
            # Natural language - show help
            help_text = """
**Intelligent Compression Agent** 🧠🗜️

I parse rough noisy text (JSON, HTML, scraped data) from research agents and build a market-centric compressed graph.

**How to use:**

Send JSON with:
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "protected_terms": ["France", "World Cup", "2026"],
  "evidence_chunks": [
    {
      "source_type": "sports_video",
      "text": "{\"game\": {\"competitors\": [{\"team\": \"France\", \"score\": 2}...]}}",
      "source_url": "https://espn.com/...",
      "confidence": 0.8
    }
  ],
  "token_budget": 200,
  "output_format": "text"
}
```

**What I do:**
1. **Parse noisy data** - Extract clean facts from JSON/HTML/scraped text
2. **Build market graph** - Market question as central node
3. **Classify relationships** - Each fact → supports/contradicts/neutral
4. **Deduplicate** - Merge similar facts
5. **Compress** - 3-10x compression while preserving key evidence

**Supported formats:**
- ESPN JSON (sports_video)
- Kalshi JSON (financial_research)
- Browserbase HTML scrapes
- Plain text

**Output formats:**
- `"text"` - Ultra-compact text (Q: ... YES: ... NO: ...)
- `"json"` - Full graph JSON with market + facts + relationships

Try sending real noisy data from research agents!
"""
            response_msg = ChatMessage(content=[TextContent(text=help_text)])
            await ctx.send(sender, response_msg)

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Chat error: {e}")
        ctx.logger.error(traceback.format_exc())

        error_msg = ChatMessage(content=[TextContent(text=f"Error: {str(e)}")])
        await ctx.send(sender, error_msg)


@chat_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    """Handle ACK messages"""
    ctx.logger.info(f"[{AGENT_NAME}] ACK from {sender}")


# ============================================================================
# CUSTOM PROTOCOL (Orchestrator)
# ============================================================================

compression_protocol = Protocol(name="IntelligentCompression")


@compression_protocol.on_message(model=CompressionRequest)
async def handle_compression_request(ctx: Context, sender: str, msg: CompressionRequest):
    """Handle compression requests from orchestrator"""
    ctx.logger.info(f"[{AGENT_NAME}] Compression request from {sender}")
    ctx.logger.info(f"Market: {msg.market_question}")
    ctx.logger.info(f"Chunks: {len(msg.evidence_chunks)}")

    try:
        # Convert evidence chunks to dict format
        evidence_chunks = []
        for chunk in msg.evidence_chunks:
            evidence_chunks.append({
                "source_type": chunk.source_type,
                "text": chunk.text,
                "source_url": chunk.source_url,
                "confidence": chunk.confidence,
                "metadata": chunk.metadata or {}
            })

        # Compress
        compressed_output, metrics = compressor.compress(
            market_question=msg.market_question,
            protected_terms=msg.protected_terms,
            evidence_chunks=evidence_chunks,
            token_budget=msg.token_budget,
            output_format="text"  # Always text for orchestrator
        )

        # Build response
        response = CompressionResponse(
            request_id=msg.msg_id,
            raw_token_count=metrics['raw_tokens'],
            compressed_token_count=metrics['compressed_tokens'],
            compression_ratio=metrics['compression_ratio'],
            compressed_context=compressed_output,
            kept_chunks_count=metrics['facts_final'],
            dropped_chunks_count=metrics['facts_extracted'] - metrics['facts_final'],
            protected_terms=msg.protected_terms
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Compression complete:")
        ctx.logger.info(f"  Compression ratio: {metrics['compression_ratio']}x")
        ctx.logger.info(f"  Facts: {metrics['facts_extracted']} → {metrics['facts_final']}")
        ctx.logger.info(f"  Market-centric: {metrics['supporting_facts']} YES, {metrics['contradicting_facts']} NO")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Compression failed: {e}")
        ctx.logger.error(traceback.format_exc())

        # Send error response
        error_response = CompressionResponse(
            request_id=msg.msg_id,
            raw_token_count=0,
            compressed_token_count=0,
            compression_ratio=0.0,
            compressed_context=f"Error: {str(e)}",
            kept_chunks_count=0,
            dropped_chunks_count=0,
            protected_terms=msg.protected_terms
        )

        await ctx.send(sender, error_response)


# ============================================================================
# REGISTER PROTOCOLS
# ============================================================================

agent.include(chat_protocol, publish_manifest=True)
agent.include(compression_protocol, publish_manifest=True)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(f"Starting {AGENT_NAME}")
    print(f"Agent address: {agent.address}")
    print(f"Mailbox: {AGENT_MAILBOX}")
    print("=" * 80)
    print()
    print("Features:")
    print("  ✅ Parses rough noisy JSON/HTML/text")
    print("  ✅ Extracts clean facts from research agent data")
    print("  ✅ Builds market-centric graph")
    print("  ✅ Classifies fact-to-market relationships")
    print("  ✅ Achieves 3-10x compression")
    print("  ✅ Dual protocols: Chat (ASI:One) + Custom (Orchestrator)")
    print("=" * 80)
    agent.run()
