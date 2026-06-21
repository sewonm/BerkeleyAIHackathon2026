"""
Advanced Compression uAgent - Graph-consensus compression with information-theoretic scoring.

This agent implements sophisticated compression:
- Claim extraction (Claude or heuristic)
- Evidence graph construction
- Consensus clustering
- Information-value scoring
- Contradiction detection
- Missing information identification

Deployable to Agentverse as an independent service.
"""

import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from uagents import Agent, Context, Protocol
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any

# Import compression logic
from app.compression.advanced_compressor import AdvancedCompressor
from app.compression.schemas_advanced import (
    EnhancedEvidenceChunk,
    EnhancedCompressionRequest,
    EnhancedCompressionResponse,
)

# Agent configuration
AGENT_NAME = "compression_agent_advanced"
AGENT_SEED = "compression_agent_advanced_seed_change_in_production"
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
compression_protocol = Protocol("AdvancedContextCompression")

# Initialize compressor (use Claude if available)
compressor = AdvancedCompressor(use_claude=True)


@compression_protocol.on_message(model=EnhancedCompressionRequest)
async def handle_compression_request(ctx: Context, sender: str, msg: EnhancedCompressionRequest):
    """
    Handle advanced compression requests.

    Args:
        ctx: Agent context
        sender: Address of requesting agent
        msg: Compression request message
    """
    ctx.logger.info(f"[{AGENT_NAME}] Received compression request from {sender}")
    ctx.logger.info(f"Market ID: {msg.market_id}")
    ctx.logger.info(f"Evidence chunks: {len(msg.evidence_chunks)}")
    ctx.logger.info(f"Mode: {msg.mode}")

    try:
        # Run compression
        result = compressor.compress(msg)

        # Send response
        response = EnhancedCompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="success",
            compression_result=result
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Compression complete")
        ctx.logger.info(f"  Raw tokens: {result.metrics.raw_token_count}")
        ctx.logger.info(f"  Compressed tokens: {result.metrics.compressed_token_count}")
        ctx.logger.info(f"  Ratio: {result.metrics.compression_ratio:.2f}x")
        ctx.logger.info(f"  Claims extracted: {result.metrics.total_claims_extracted}")
        ctx.logger.info(f"  Consensus items: {result.metrics.total_consensus_items}")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Compression failed: {e}")
        ctx.logger.error(traceback.format_exc())

        # Send error response
        response = EnhancedCompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="error",
            error=str(e)
        )

        await ctx.send(sender, response)


# Include protocol
agent.include(compression_protocol)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Advanced Compression Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Mode: Graph-Consensus Compression with Information-Theoretic Scoring")
    ctx.logger.info(f"Ready to compress evidence contexts")

    # Check if Claude is available
    if compressor.use_claude and compressor.claim_extractor.client:
        ctx.logger.info("Claude extraction: ENABLED")
    else:
        ctx.logger.info("Claude extraction: DISABLED (using heuristic fallback)")


if __name__ == "__main__":
    agent.run()
