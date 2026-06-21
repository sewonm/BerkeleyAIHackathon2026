#!/usr/bin/env python3
"""Test graph compression agent"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from graph_compression_agent import GraphCompressor

def test_graph_compression():
    """Test the graph compressor"""

    print("=" * 80)
    print("GRAPH COMPRESSION TEST")
    print("=" * 80)
    print()

    # Create test evidence chunks (one per source)
    evidence_chunks = [
        {
            "chunk_id": "1",
            "market_id": "france-wc",
            "source_agent": "sports_video_agent",
            "source_type": "sports_video",
            "text": "France defeated Brazil 2-1 in a thrilling match yesterday. Mbappe scored twice in the second half."
        },
        {
            "chunk_id": "2",
            "market_id": "france-wc",
            "source_agent": "news_agent",
            "source_type": "news",
            "text": "France beat Brazil with a 2-1 score. Mbappe's performance was exceptional with two goals."
        },
        {
            "chunk_id": "3",
            "market_id": "france-wc",
            "source_agent": "odds_agent",
            "source_type": "betting_odds",
            "text": "Current betting odds favor France at 62% implied probability. Market has shifted 5% towards France."
        },
        {
            "chunk_id": "4",
            "market_id": "france-wc",
            "source_agent": "injury_agent",
            "source_type": "injuries",
            "text": "Key midfielder Pogba is nursing a minor injury and is questionable for the next match."
        },
        {
            "chunk_id": "5",
            "market_id": "france-wc",
            "source_agent": "stats_agent",
            "source_type": "stats",
            "text": "France has won 4 out of their last 5 matches against top-ranked opponents."
        }
    ]

    print(f"INPUT: {len(evidence_chunks)} evidence chunks from different sources")
    print()
    for chunk in evidence_chunks:
        print(f"  {chunk['source_agent']}: {chunk['text'][:60]}...")
    print()

    # Create compressor
    compressor = GraphCompressor(similarity_threshold=0.6)

    # Test text output
    print("-" * 80)
    print("TEXT OUTPUT (token budget: 100)")
    print("-" * 80)
    compressed_text, metrics = compressor.compress(
        evidence_chunks=evidence_chunks,
        market_question="Will France win the World Cup 2026?",
        token_budget=100,
        output_format="text"
    )

    print()
    print("COMPRESSED OUTPUT:")
    print(compressed_text)
    print()

    print("METRICS:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print()

    if metrics['compression_ratio'] >= 1.0:
        print(f"✅ Compression achieved: {metrics['compression_ratio']}x")
    else:
        print(f"⚠️  Expansion: {metrics['compression_ratio']}x")
    print()

    # Test JSON output
    print("-" * 80)
    print("JSON OUTPUT")
    print("-" * 80)
    compressed_json, metrics_json = compressor.compress(
        evidence_chunks=evidence_chunks,
        market_question="Will France win the World Cup 2026?",
        token_budget=200,
        output_format="json"
    )

    print()
    print("COMPRESSED GRAPH:")
    import json
    graph = json.loads(compressed_json)
    print(json.dumps(graph, indent=2))
    print()

    print("GRAPH SUMMARY:")
    print(f"  Nodes: {len(graph['nodes'])}")
    print(f"  Edges: {len(graph['edges'])}")
    print()

    print("RELATIONSHIP TYPES:")
    edge_types = {}
    for edge in graph['edges']:
        edge_type = edge['type']
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
    for edge_type, count in edge_types.items():
        print(f"  {edge_type}: {count}")
    print()

    # Final validation
    print("=" * 80)
    print("FINAL VALIDATION")
    print("=" * 80)
    print()

    success = metrics['compression_ratio'] >= 1.2  # At least 1.2x compression

    if success:
        print("✅ ✅ ✅ GRAPH COMPRESSION SUCCESSFUL! ✅ ✅ ✅")
        print(f"Achieved {metrics['compression_ratio']}x compression")
        print(f"Merged {metrics['merged_sources']} redundant sources")
        print(f"Deleted {metrics['deleted_sources']} low-value sources")
        print(f"Final output: {metrics['final_sources']} sources with {metrics['relationships']} relationships")
        return True
    else:
        print("❌ Compression failed")
        return False


if __name__ == "__main__":
    success = test_graph_compression()
    sys.exit(0 if success else 1)
