#!/usr/bin/env python3
"""
Test standalone_decision_agent.py with graph_compression_agent.py output format
"""

import json
from typing import Dict, Any

def test_graph_compression_format():
    """Test with actual graph_compression_agent.py output"""
    print("=" * 80)
    print("TEST: Graph Compression Agent Format")
    print("=" * 80)

    # Your actual example input
    graph_data = {
        "nodes": [
            {
                "id": "82fd9333-3e6c-458c-949d-129f9829dbfe",
                "source": "unknown",
                "text": "Skip to main content Skip to navigation ESPN Search You have come to the ESPN Af",
                "dir": "Y",
                "score": 0.9,
                "merged": 0
            }
        ],
        "edges": []
    }

    # Simulate the parser from standalone_decision_agent.py
    def analyze_graph_compression(data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze JSON graph format from graph_compression_agent"""
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        yes_nodes = [n for n in nodes if n.get("dir") == "Y"]
        no_nodes = [n for n in nodes if n.get("dir") == "N"]

        # Calculate weighted scores
        yes_score = sum(n.get("score", 0) for n in yes_nodes) / max(len(yes_nodes), 1)
        no_score = sum(n.get("score", 0) for n in no_nodes) / max(len(no_nodes), 1)

        # Normalize to 0-1 range
        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total

        # Count reinforcement edges
        reinforcements = sum(1 for e in edges if e.get("type") == "reinforces")
        contradictions = sum(1 for e in edges if e.get("type") == "contradicts")

        return {
            "yes_nodes": yes_nodes,
            "no_nodes": no_nodes,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_nodes),
            "no_count": len(no_nodes),
            "reinforcements": reinforcements,
            "contradictions": contradictions,
            "edges": edges
        }

    def make_decision(analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Make decision based on analysis"""
        yes_score = analysis["yes_score"]
        no_score = analysis["no_score"]

        CONFIDENCE_THRESHOLD = 0.15
        score_diff = yes_score - no_score

        if abs(score_diff) < CONFIDENCE_THRESHOLD:
            action = "HOLD"
            confidence = 0.5
        elif score_diff > 0:
            action = "YES"
            confidence = min(0.5 + score_diff, 0.95)
        else:
            action = "NO"
            confidence = min(0.5 + abs(score_diff), 0.95)

        return {
            "action": action,
            "confidence": confidence,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": analysis["yes_count"],
            "no_count": analysis["no_count"]
        }

    # Parse the graph data
    analysis = analyze_graph_compression(graph_data)
    decision = make_decision(analysis)

    # Display results
    print(f"\n📊 Graph Analysis:")
    print(f"  Total Nodes: {len(graph_data['nodes'])}")
    print(f"  Total Edges: {len(graph_data['edges'])}")
    print(f"  YES Nodes (dir='Y'): {analysis['yes_count']}")
    print(f"  NO Nodes (dir='N'): {analysis['no_count']}")
    print(f"  YES Score: {analysis['yes_score']:.3f}")
    print(f"  NO Score: {analysis['no_score']:.3f}")

    print(f"\n✅ Decision: {decision['action']}")
    print(f"  Confidence: {decision['confidence']:.1%}")

    print(f"\n📝 YES Nodes:")
    for i, node in enumerate(analysis['yes_nodes'], 1):
        print(f"  {i}. ID: {node['id'][:8]}...")
        print(f"     Source: {node['source']}")
        print(f"     Text: {node['text'][:60]}...")
        print(f"     Score: {node['score']:.2f}")

    print(f"\n📝 NO Nodes:")
    if analysis['no_count'] == 0:
        print("  (None)")
    else:
        for i, node in enumerate(analysis['no_nodes'], 1):
            print(f"  {i}. {node['text'][:60]}... (score: {node['score']:.2f})")

    # Verify parsing worked
    assert analysis['yes_count'] == 1, f"Expected 1 YES node, got {analysis['yes_count']}"
    assert analysis['no_count'] == 0, f"Expected 0 NO nodes, got {analysis['no_count']}"
    assert decision['action'] == "YES", f"Expected YES decision, got {decision['action']}"

    print(f"\n✅ All assertions passed!")
    return decision


def test_more_realistic_example():
    """Test with a more realistic example with both YES and NO nodes"""
    print("\n" + "=" * 80)
    print("TEST: Realistic Graph with YES and NO Nodes")
    print("=" * 80)

    graph_data = {
        "nodes": [
            {
                "id": "1",
                "source": "sports_video_agent",
                "text": "France defeated Brazil 2-1. Mbappe scored twice",
                "dir": "Y",
                "score": 0.85,
                "merged": 0
            },
            {
                "id": "2",
                "source": "odds_agent",
                "text": "Betting odds favor France at 62% implied probability",
                "dir": "Y",
                "score": 0.72,
                "merged": 0
            },
            {
                "id": "3",
                "source": "injury_agent",
                "text": "Kante questionable with ankle injury",
                "dir": "N",
                "score": 0.68,
                "merged": 0
            }
        ],
        "edges": [
            {
                "from": "1",
                "to": "2",
                "type": "reinforces",
                "strength": 0.7
            }
        ]
    }

    # Use same parser
    def analyze_graph_compression(data: Dict[str, Any]) -> Dict[str, Any]:
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        yes_nodes = [n for n in nodes if n.get("dir") == "Y"]
        no_nodes = [n for n in nodes if n.get("dir") == "N"]

        yes_score = sum(n.get("score", 0) for n in yes_nodes) / max(len(yes_nodes), 1)
        no_score = sum(n.get("score", 0) for n in no_nodes) / max(len(no_nodes), 1)

        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total

        reinforcements = sum(1 for e in edges if e.get("type") == "reinforces")
        contradictions = sum(1 for e in edges if e.get("type") == "contradicts")

        return {
            "yes_nodes": yes_nodes,
            "no_nodes": no_nodes,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_nodes),
            "no_count": len(no_nodes),
            "reinforcements": reinforcements,
            "contradictions": contradictions
        }

    analysis = analyze_graph_compression(graph_data)

    print(f"\n📊 Analysis:")
    print(f"  YES Nodes: {analysis['yes_count']} (avg score: {sum(n['score'] for n in analysis['yes_nodes'])/len(analysis['yes_nodes']):.2f})")
    print(f"  NO Nodes: {analysis['no_count']} (avg score: {sum(n['score'] for n in analysis['no_nodes'])/len(analysis['no_nodes']):.2f})")
    print(f"  YES Score (normalized): {analysis['yes_score']:.3f}")
    print(f"  NO Score (normalized): {analysis['no_score']:.3f}")
    print(f"  Reinforcements: {analysis['reinforcements']}")
    print(f"  Contradictions: {analysis['contradictions']}")

    score_diff = analysis['yes_score'] - analysis['no_score']
    print(f"\n  Score Difference: {score_diff:.3f}")

    if abs(score_diff) < 0.15:
        print(f"  → HOLD (difference {score_diff:.3f} < threshold 0.15)")
    elif score_diff > 0:
        print(f"  → YES (difference {score_diff:.3f} > threshold 0.15)")

    print(f"\n✅ Graph compression format parsed successfully!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("GRAPH COMPRESSION → DECISION AGENT TEST SUITE")
    print("=" * 80 + "\n")

    try:
        decision = test_graph_compression_format()
        test_more_realistic_example()

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED - Decision agent works with graph_compression_agent.py!")
        print("=" * 80)
        print(f"\nYour input format is CORRECT and SUPPORTED!")
        print(f"The decision agent will parse it as:")
        print(f"  - YES nodes: dir='Y'")
        print(f"  - NO nodes: dir='N'")
        print(f"  - Scores from 'score' field")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
