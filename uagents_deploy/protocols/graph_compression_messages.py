"""
graph_compression_messages.py — wire-compatible mirror of graph_compression_agent.py's
message models.

WHY THIS EXISTS:
The orchestrator's shared protocols.messages.CompressionRequest/Response have a DIFFERENT
schema than the ones graph_compression_agent.py declares locally (different field names,
types, and a different nested chunk type). uAgents routes messages by a schema digest
computed over the model name + every field + type, so the orchestrator's shared message
would never reach the graph agent's handler.

These classes are byte-for-byte identical (names, fields, types, defaults, docstrings) to
the models in graph_compression_agent.py, so they produce the SAME schema digest. The
orchestrator imports THESE to talk to the graph compressor — the graph agent itself is
left untouched.

If graph_compression_agent.py's models ever change, update this file to match (a digest
parity test lives alongside the orchestrator changes).
"""

from typing import List, Dict, Any, Optional

from uagents import Model


class EvidenceChunk(Model):
    """Input: One chunk per source"""
    chunk_id: str
    market_id: str
    source_agent: str
    source_type: str
    text: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CompressionRequest(Model):
    """Request to compress evidence"""
    request_id: str
    market_id: str
    market_question: str
    resolution_criteria: str = ""
    evidence_chunks: List[EvidenceChunk]
    token_budget: int = 200
    output_format: str = "text"  # "text" or "json"


class CompressionResponse(Model):
    """Response with compressed graph"""
    request_id: str
    market_id: str
    status: str  # "success" or "error"
    compressed_output: str
    metrics: Dict[str, Any]
    error: Optional[str] = None
