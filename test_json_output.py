#!/usr/bin/env python3
"""
Test script to verify JSON graph output from compression agent
"""

import sys
import os

# Add the uagents_deploy directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from standalone_compression_agent import (
    AdvancedCompressor,
    EnhancedCompressionRequest,
    EnhancedEvidenceChunk
)
import json

def test_json_output():
    """Test that the compression agent produces valid JSON graph output"""

    print("=" * 80)
    print("Testing Compression Agent JSON Graph Output")
    print("=" * 80)
    print()

    # Create compressor
    compressor = AdvancedCompressor(use_claude=False)  # Use heuristic to avoid API calls

    # Create test evidence chunks
    chunks = [
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="sports_video_agent",
            source_type="sports_video",
            text="France defeated Brazil 2-1 in a thrilling match yesterday. Mbappe scored twice in the second half, showing exceptional form. The French defense held strong against Brazil's attacks."
        ),
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="odds_agent",
            source_type="betting_odds",
            text="Current betting odds favor France at 58% implied probability. Odds have shifted 5% in favor over the past week."
        ),
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="news_agent",
            source_type="news",
            text="However, France struggled in their last friendly match, barely winning 1-0 against a lower-ranked team. Key midfielder Pogba is nursing a minor injury."
        )
    ]

    # Create compression request
    request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will France win the World Cup 2026?",
        resolution_criteria="Resolves YES if France wins the 2026 FIFA World Cup",
        current_yes_price=0.62,
        current_no_price=0.38,
        evidence_chunks=chunks,
        aggressiveness=0.5
    )

    print("Processing compression...")
    print(f"- Market: {request.market_question}")
    print(f"- Evidence chunks: {len(chunks)}")
    print(f"- Aggressiveness: {request.aggressiveness}")
    print()

    # Compress
    result = compressor.compress(request)

    print("Compression complete!")
    print()
    print("METRICS:")
    print(f"  Raw tokens: {result.metrics.raw_token_count}")
    print(f"  Compressed tokens: {result.metrics.compressed_token_count}")
    print(f"  Compression ratio: {result.metrics.compression_ratio:.2f}x")
    print(f"  Claims extracted: {result.metrics.total_claims_extracted}")
    print(f"  Consensus items: {result.metrics.total_consensus_items}")
    print(f"  Graph nodes: {result.metrics.graph_node_count}")
    print(f"  Graph edges: {result.metrics.graph_edge_count}")
    print()

    # Build JSON output (same as in the chat handler)
    graph_json = {
        "result_id": result.result_id,
        "request_id": result.request_id,
        "market_id": result.market_id,
        "mode": result.mode,
        "timestamp": result.timestamp.isoformat(),

        "evidence_graph": {
            "graph_id": result.evidence_graph.graph_id,
            "market_id": result.evidence_graph.market_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "label": node.label,
                    "properties": node.properties
                }
                for node in result.evidence_graph.nodes
            ],
            "edges": [
                {
                    "edge_id": edge.edge_id,
                    "edge_type": edge.edge_type,
                    "source_node_id": edge.source_node_id,
                    "target_node_id": edge.target_node_id,
                    "weight": edge.weight,
                    "properties": edge.properties
                }
                for edge in result.evidence_graph.edges
            ]
        },

        "consensus_ledger": {
            "ledger_id": result.consensus_ledger.ledger_id,
            "market_id": result.consensus_ledger.market_id,
            "consensus_items": [
                {
                    "consensus_id": item.consensus_id,
                    "canonical_claim": item.canonical_claim,
                    "direction": item.direction,
                    "source_count": item.source_count,
                    "source_agents": item.source_agents,
                    "source_diversity_score": item.source_diversity_score,
                    "agreement_level": item.agreement_level,
                    "consensus_entropy": item.consensus_entropy,
                    "confidence": item.confidence,
                    "estimated_probability_shift": item.estimated_probability_shift,
                    "information_value": item.information_value,
                    "supporting_claim_ids": item.supporting_claim_ids,
                    "opposing_claim_ids": item.opposing_claim_ids,
                    "entities": item.entities
                }
                for item in result.consensus_ledger.consensus_items
            ]
        },

        "top_supporting_evidence": [
            {
                "consensus_id": item.consensus_id,
                "canonical_claim": item.canonical_claim,
                "direction": item.direction,
                "information_value": item.information_value,
                "source_count": item.source_count,
                "agreement_level": item.agreement_level
            }
            for item in result.top_supporting_evidence
        ],
        "top_opposing_evidence": [
            {
                "consensus_id": item.consensus_id,
                "canonical_claim": item.canonical_claim,
                "direction": item.direction,
                "information_value": item.information_value,
                "source_count": item.source_count,
                "agreement_level": item.agreement_level
            }
            for item in result.top_opposing_evidence
        ],

        "contradictions": result.contradictions,
        "missing_info": result.missing_info,
        "compressed_context": result.compressed_context,

        "metrics": {
            "raw_token_count": result.metrics.raw_token_count,
            "compressed_token_count": result.metrics.compressed_token_count,
            "compression_ratio": result.metrics.compression_ratio,
            "token_budget": result.metrics.token_budget,
            "total_claims_extracted": result.metrics.total_claims_extracted,
            "total_consensus_items": result.metrics.total_consensus_items,
            "yes_consensus_count": result.metrics.yes_consensus_count,
            "no_consensus_count": result.metrics.no_consensus_count,
            "neutral_consensus_count": result.metrics.neutral_consensus_count,
            "graph_node_count": result.metrics.graph_node_count,
            "graph_edge_count": result.metrics.graph_edge_count,
            "claude_calls": result.metrics.claude_calls,
            "claude_failures": result.metrics.claude_failures,
            "heuristic_fallbacks": result.metrics.heuristic_fallbacks
        }
    }

    print("JSON GRAPH STRUCTURE:")
    print("=" * 80)
    print(json.dumps(graph_json, indent=2))
    print("=" * 80)
    print()

    # Validate it's valid JSON
    try:
        json_str = json.dumps(graph_json)
        parsed = json.loads(json_str)
        print("✅ JSON output is valid and parseable!")
        print()

        # Show summary
        print("GRAPH SUMMARY:")
        print(f"  Total nodes: {len(parsed['evidence_graph']['nodes'])}")
        print(f"  Total edges: {len(parsed['evidence_graph']['edges'])}")
        print(f"  Consensus items: {len(parsed['consensus_ledger']['consensus_items'])}")
        print(f"  Top YES evidence: {len(parsed['top_supporting_evidence'])}")
        print(f"  Top NO evidence: {len(parsed['top_opposing_evidence'])}")
        print(f"  Contradictions: {len(parsed['contradictions'])}")
        print()

        # Show node types
        node_types = {}
        for node in parsed['evidence_graph']['nodes']:
            node_type = node['node_type']
            node_types[node_type] = node_types.get(node_type, 0) + 1

        print("NODE TYPES:")
        for node_type, count in sorted(node_types.items()):
            print(f"  {node_type}: {count}")
        print()

        # Show edge types
        edge_types = {}
        for edge in parsed['evidence_graph']['edges']:
            edge_type = edge['edge_type']
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        print("EDGE TYPES:")
        for edge_type, count in sorted(edge_types.items()):
            print(f"  {edge_type}: {count}")
        print()

        print("✅ Test passed! JSON graph output is working correctly.")
        return True

    except Exception as e:
        print(f"❌ JSON validation failed: {e}")
        return False


if __name__ == "__main__":
    success = test_json_output()
    sys.exit(0 if success else 1)
