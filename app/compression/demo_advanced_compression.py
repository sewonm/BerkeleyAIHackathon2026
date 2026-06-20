"""
Local demo for advanced compression pipeline.

Run this to test the compression logic without uAgents/Agentverse.
"""

import json
import os
from datetime import datetime

from app.compression.advanced_compressor import AdvancedCompressor
from app.compression.schemas_advanced import (
    EnhancedEvidenceChunk,
    EnhancedCompressionRequest,
)


def load_sample_evidence() -> list:
    """Load sample evidence from the culture_web_context file"""
    sample_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "examples",
        "raw_context",
        "culture_web_context.txt"
    )

    if not os.path.exists(sample_file_path):
        print(f"Warning: Sample file not found at {sample_file_path}")
        return []

    with open(sample_file_path, 'r') as f:
        raw_text = f.read()

    # Split into paragraphs
    paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip() and len(p.split()) > 10]

    # Convert to evidence chunks
    chunks = []
    for i, para in enumerate(paragraphs[:20]):  # Limit to 20 for demo
        chunk = EnhancedEvidenceChunk(
            market_id="demo-oscars-2027",
            source_agent="culture_web_agent",
            source_type="culture_web",
            text=para,
            source_url="local://examples/raw_context/culture_web_context.txt",
            confidence=0.8,
            metadata={"chunk_index": i}
        )
        chunks.append(chunk)

    return chunks


def run_demo():
    """Run the compression demo"""
    print("="* 80)
    print("ADVANCED COMPRESSION PIPELINE DEMO")
    print("="* 80)
    print()

    # Load sample evidence
    print("Loading sample evidence...")
    evidence_chunks = load_sample_evidence()
    print(f"Loaded {len(evidence_chunks)} evidence chunks")
    print()

    # Create compression request
    request = EnhancedCompressionRequest(
        market_id="demo-oscars-2027",
        market_question="Will 'Stellar Dreams' win Best Picture at the 2027 Academy Awards?",
        resolution_criteria="Market resolves YES if 'Stellar Dreams' officially wins the Academy Award for Best Picture at the 2027 Oscars ceremony.",
        current_yes_price=0.42,
        current_no_price=0.58,
        evidence_chunks=evidence_chunks,
        token_budget=3000,
        mode="graph-consensus"
    )

    # Initialize compressor
    print("Initializing Advanced Compressor...")
    compressor = AdvancedCompressor(use_claude=True)
    print()

    # Run compression
    print("Running compression pipeline...")
    print()
    result = compressor.compress(request)
    print()

    # Display results
    print("="* 80)
    print("COMPRESSION RESULTS")
    print("="* 80)
    print()

    print("METRICS:")
    print(f"  Raw tokens: {result.metrics.raw_token_count:,}")
    print(f"  Compressed tokens: {result.metrics.compressed_token_count:,}")
    print(f"  Compression ratio: {result.metrics.compression_ratio:.2f}x")
    print(f"  Token budget: {result.metrics.token_budget:,}")
    print()

    print("EXTRACTION:")
    print(f"  Total claims extracted: {result.metrics.total_claims_extracted}")
    print(f"  Claude calls: {result.metrics.claude_calls}")
    print(f"  Heuristic fallbacks: {result.metrics.heuristic_fallbacks}")
    print()

    print("CONSENSUS:")
    print(f"  Total consensus items: {result.metrics.total_consensus_items}")
    print(f"  YES consensus: {result.metrics.yes_consensus_count}")
    print(f"  NO consensus: {result.metrics.no_consensus_count}")
    print(f"  NEUTRAL consensus: {result.metrics.neutral_consensus_count}")
    print()

    print("GRAPH:")
    print(f"  Nodes: {result.metrics.graph_node_count}")
    print(f"  Edges: {result.metrics.graph_edge_count}")
    print()

    print("="* 80)
    print("COMPRESSED CONTEXT")
    print("="* 80)
    print()
    print(result.compressed_context)
    print()

    # Save full result to JSON
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "examples",
        "outputs"
    )
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "advanced_compression_result.json")

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "request": {
            "market_id": request.market_id,
            "market_question": request.market_question,
            "mode": request.mode,
            "chunk_count": len(request.evidence_chunks)
        },
        "metrics": result.metrics.model_dump(),
        "evidence_graph": {
            "node_count": len(result.evidence_graph.nodes),
            "edge_count": len(result.evidence_graph.edges),
            "nodes": [n.model_dump() for n in result.evidence_graph.nodes[:10]],  # Sample
            "edges": [e.model_dump() for e in result.evidence_graph.edges[:10]],  # Sample
        },
        "consensus_ledger": {
            "total_items": len(result.consensus_ledger.consensus_items),
            "top_yes": [item.model_dump() for item in result.top_supporting_evidence],
            "top_no": [item.model_dump() for item in result.top_opposing_evidence],
        },
        "contradictions": result.contradictions,
        "missing_info": result.missing_info,
        "compressed_context": result.compressed_context,
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print("="* 80)
    print(f"Full result saved to: {output_file}")
    print("="* 80)


if __name__ == "__main__":
    run_demo()
