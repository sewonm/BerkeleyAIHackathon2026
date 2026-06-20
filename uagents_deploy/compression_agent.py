"""
CompressionAgent - Standalone uAgent for context compression.

This agent receives raw evidence chunks and compresses them into
a compact, decision-ready context while preserving important information.

Deployable to Agentverse as an independent service.
"""

from uagents import Agent, Context, Protocol
from protocols.messages import (
    CompressionRequest,
    CompressionResponse,
    AgentStatus
)

# Import compression logic from main app
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.compression.compressor import Compressor
from app.compression.scorer import ChunkScorer
from app.compression.protected_terms import extract_key_words
from app.schemas.evidence import EvidenceChunk
from app.schemas.market import Market
from app.utils.dedupe import deduplicate_chunks

# Agent configuration
AGENT_NAME = "compression_agent"
AGENT_SEED = "compression_agent_seed_phrase_change_in_production"
AGENT_PORT = 8002
AGENT_MAILBOX = True

# Create the agent
agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
)

# Create protocol
compression_protocol = Protocol("ContextCompression")

# Initialize compressor
compressor = Compressor()


@compression_protocol.on_message(model=CompressionRequest)
async def handle_compression_request(ctx: Context, sender: str, msg: CompressionRequest):
    """
    Handle compression requests.

    Args:
        ctx: Agent context
        sender: Address of requesting agent
        msg: Compression request message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received compression request from {sender}")
    ctx.logger.info(f"Evidence chunks: {len(msg.evidence_chunks)}")
    ctx.logger.info(f"Token budget: {msg.token_budget}")

    # Send processing status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="processing",
        message=f"Compressing {len(msg.evidence_chunks)} evidence chunks"
    ))

    # Convert message chunks to EvidenceChunk objects
    evidence_chunks = []
    for chunk_msg in msg.evidence_chunks:
        evidence_chunks.append(EvidenceChunk(
            source_type=chunk_msg.source_type,
            text=chunk_msg.text,
            source_url=chunk_msg.source_url,
            timestamp=chunk_msg.timestamp,
            confidence=chunk_msg.confidence,
            metadata=chunk_msg.metadata
        ))

    # Create a temporary market object for compression
    temp_market = Market(
        market_id="temp",
        title="Temporary Market",
        question=msg.market_question,
        category="general",
        resolution_criteria="N/A",
        protected_terms=msg.protected_terms
    )

    # Perform compression
    compression_result = compressor.compress(
        market=temp_market,
        evidence_chunks=evidence_chunks,
        token_budget=msg.token_budget
    )

    ctx.logger.info(f"[{AGENT_NAME}] Compression complete")
    ctx.logger.info(f"Raw tokens: {compression_result.raw_token_count}")
    ctx.logger.info(f"Compressed tokens: {compression_result.compressed_token_count}")
    ctx.logger.info(f"Ratio: {compression_result.compression_ratio:.2f}x")

    # Send response
    response = CompressionResponse(
        request_id=msg.msg_id,
        raw_token_count=compression_result.raw_token_count,
        compressed_token_count=compression_result.compressed_token_count,
        compression_ratio=compression_result.compression_ratio,
        compressed_context=compression_result.compressed_context,
        kept_chunks_count=len(compression_result.kept_chunks),
        dropped_chunks_count=len(compression_result.dropped_chunks),
        protected_terms=compression_result.protected_terms
    )

    await ctx.send(sender, response)

    # Send completion status
    await ctx.send(sender, AgentStatus(
        agent_name=AGENT_NAME,
        status="completed",
        message=f"Compressed {compression_result.compression_ratio:.2f}x"
    ))


# Include protocol
agent.include(compression_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Ready to compress evidence contexts")


if __name__ == "__main__":
    agent.run()
