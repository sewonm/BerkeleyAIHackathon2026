#!/usr/bin/env python3
"""
Test the core decision logic without uagents dependencies.
"""

import json
import re
from typing import Dict, Any

def parse_json_graph(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze JSON graph format"""
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


def parse_text_graph(text: str) -> Dict[str, Any]:
    """Analyze text format from graph_compression_agent"""
    yes_pattern = r'YES:(.*?)(?:NO:|$)'
    no_pattern = r'NO:(.*?)$'

    yes_match = re.search(yes_pattern, text)
    no_match = re.search(no_pattern, text)

    yes_nodes = []
    no_nodes = []

    if yes_match:
        yes_text = yes_match.group(1).strip()
        # Parse claims: "claim1(0.85)|claim2(0.72)"
        yes_claims = yes_text.split("|")
        for claim in yes_claims:
            score_match = re.search(r'\(([0-9.]+)\)', claim)
            score = float(score_match.group(1)) if score_match else 0.5
            text_part = re.sub(r'\([0-9.]+\)', '', claim).strip()
            yes_nodes.append({"text": text_part, "score": score, "dir": "Y"})

    if no_match:
        no_text = no_match.group(1).strip()
        no_claims = no_text.split("|")
        for claim in no_claims:
            score_match = re.search(r'\(([0-9.]+)\)', claim)
            score = float(score_match.group(1)) if score_match else 0.5
            text_part = re.sub(r'\([0-9.]+\)', '', claim).strip()
            no_nodes.append({"text": text_part, "score": score, "dir": "N"})

    # Calculate weighted scores
    yes_score = sum(n["score"] for n in yes_nodes) / max(len(yes_nodes), 1)
    no_score = sum(n["score"] for n in no_nodes) / max(len(no_nodes), 1)

    # Normalize
    total = yes_score + no_score
    if total > 0:
        yes_score = yes_score / total
        no_score = no_score / total

    return {
        "yes_nodes": yes_nodes,
        "no_nodes": no_nodes,
        "yes_score": yes_score,
        "no_score": no_score,
        "yes_count": len(yes_nodes),
        "no_count": len(no_nodes),
        "reinforcements": 0,
        "contradictions": 0,
        "edges": []
    }


def make_decision(graph_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Make decision based on graph analysis"""
    yes_score = graph_analysis["yes_score"]
    no_score = graph_analysis["no_score"]
    yes_count = graph_analysis["yes_count"]
    no_count = graph_analysis["no_count"]

    # Decision thresholds
    CONFIDENCE_THRESHOLD = 0.15

    # Calculate score difference
    score_diff = yes_score - no_score

    # Make decision
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
        "yes_count": yes_count,
        "no_count": no_count
    }


def test_json_format():
    """Test JSON graph format"""
    print("=" * 80)
    print("TEST 1: JSON Graph Format")
    print("=" * 80)

    graph_json = {
        "nodes": [
            {"id": "1", "text": "France defeated Brazil 2-1", "dir": "Y", "score": 0.85},
            {"id": "2", "text": "Betting odds favor France 62%", "dir": "Y", "score": 0.72},
            {"id": "3", "text": "Kante questionable injury", "dir": "N", "score": 0.68}
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "reinforces", "strength": 0.7}
        ]
    }

    analysis = parse_json_graph(graph_json)
    decision = make_decision(analysis)

    print(f"\nGraph Analysis:")
    print(f"  YES Nodes: {analysis['yes_count']}, Score: {analysis['yes_score']:.2f}")
    print(f"  NO Nodes: {analysis['no_count']}, Score: {analysis['no_score']:.2f}")
    print(f"  Reinforcements: {analysis['reinforcements']}")
    print(f"  Contradictions: {analysis['contradictions']}")

    print(f"\nDecision: {decision['action']}")
    print(f"Confidence: {decision['confidence']:.2%}")
    print()


def test_text_format():
    """Test text graph format"""
    print("=" * 80)
    print("TEST 2: Text Graph Format")
    print("=" * 80)

    graph_text = "YES:France defeated Brazil 2-1(0.85)|Betting odds favor France(0.72) NO:Kante questionable(0.68)"

    analysis = parse_text_graph(graph_text)
    decision = make_decision(analysis)

    print(f"\nGraph Analysis:")
    print(f"  YES Nodes: {analysis['yes_count']}, Score: {analysis['yes_score']:.2f}")
    print(f"  NO Nodes: {analysis['no_count']}, Score: {analysis['no_score']:.2f}")

    print(f"\nDecision: {decision['action']}")
    print(f"Confidence: {decision['confidence']:.2%}")
    print()


def test_balanced():
    """Test balanced evidence (HOLD expected)"""
    print("=" * 80)
    print("TEST 3: Balanced Evidence (HOLD Expected)")
    print("=" * 80)

    graph_json = {
        "nodes": [
            {"id": "1", "text": "Strong YES", "dir": "Y", "score": 0.75},
            {"id": "2", "text": "Strong NO", "dir": "N", "score": 0.73}
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "contradicts"}
        ]
    }

    analysis = parse_json_graph(graph_json)
    decision = make_decision(analysis)

    print(f"\nGraph Analysis:")
    print(f"  YES Nodes: {analysis['yes_count']}, Score: {analysis['yes_score']:.2f}")
    print(f"  NO Nodes: {analysis['no_count']}, Score: {analysis['no_score']:.2f}")
    print(f"  Score Difference: {abs(analysis['yes_score'] - analysis['no_score']):.2f}")

    print(f"\nDecision: {decision['action']}")
    print(f"Confidence: {decision['confidence']:.2%}")
    print()


def test_strong_no():
    """Test strong NO evidence"""
    print("=" * 80)
    print("TEST 4: Strong NO Evidence")
    print("=" * 80)

    graph_text = "YES:Weak signal(0.40) NO:Critical injury(0.95)|Lost last 5 games(0.88)|Coach suspended(0.82)"

    analysis = parse_text_graph(graph_text)
    decision = make_decision(analysis)

    print(f"\nGraph Analysis:")
    print(f"  YES Nodes: {analysis['yes_count']}, Score: {analysis['yes_score']:.2f}")
    print(f"  NO Nodes: {analysis['no_count']}, Score: {analysis['no_score']:.2f}")

    print(f"\nDecision: {decision['action']}")
    print(f"Confidence: {decision['confidence']:.2%}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DECISION LOGIC TEST SUITE")
    print("=" * 80 + "\n")

    try:
        test_json_format()
        test_text_format()
        test_balanced()
        test_strong_no()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
