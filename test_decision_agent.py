#!/usr/bin/env python3
"""
Test script for standalone_decision_agent.py

Tests the decision engine with both JSON and text graph formats.
"""

import json
import sys
import os

# Add the uagents_deploy directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from standalone_decision_agent import DecisionEngine, TradingDecisionRequest

def test_json_graph_format():
    """Test with JSON graph format from graph_compression_agent"""
    print("=" * 80)
    print("TEST 1: JSON Graph Format")
    print("=" * 80)

    # Sample JSON graph output from graph_compression_agent
    graph_json = {
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

    request = TradingDecisionRequest(
        market_id="test-france-wc",
        market_question="Will France win the World Cup 2026?",
        resolution_criteria="Resolves YES if France wins",
        current_yes_price=0.52,
        current_no_price=0.48,
        graph_data=json.dumps(graph_json),
        max_position_size=100.0,
        risk_tolerance="moderate"
    )

    engine = DecisionEngine()
    decision = engine.make_decision(request)

    print(f"\nDecision: {decision.action}")
    print(f"Confidence: {decision.confidence:.2%}")
    print(f"YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)")
    print(f"NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)")
    print(f"\nReasoning:\n{decision.reasoning}")
    print()


def test_text_graph_format():
    """Test with text graph format from graph_compression_agent"""
    print("=" * 80)
    print("TEST 2: Text Graph Format")
    print("=" * 80)

    # Sample text output from graph_compression_agent
    graph_text = "YES:France defeated Brazil 2-1. Mbappe scored twice(0.85)|Betting odds favor France at 62% implied probability(0.72) NO:Kante questionable with ankle injury(0.68)"

    request = TradingDecisionRequest(
        market_id="test-france-wc-text",
        market_question="Will France win the World Cup 2026?",
        resolution_criteria="Resolves YES if France wins",
        current_yes_price=0.52,
        current_no_price=0.48,
        graph_data=graph_text,
        max_position_size=100.0,
        risk_tolerance="moderate"
    )

    engine = DecisionEngine()
    decision = engine.make_decision(request)

    print(f"\nDecision: {decision.action}")
    print(f"Confidence: {decision.confidence:.2%}")
    print(f"YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)")
    print(f"NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)")
    print(f"\nReasoning:\n{decision.reasoning}")
    print()


def test_balanced_evidence():
    """Test with balanced YES/NO evidence (should return HOLD)"""
    print("=" * 80)
    print("TEST 3: Balanced Evidence (HOLD Expected)")
    print("=" * 80)

    graph_json = {
        "nodes": [
            {
                "id": "1",
                "source": "agent1",
                "text": "Strong YES evidence",
                "dir": "Y",
                "score": 0.75,
                "merged": 0
            },
            {
                "id": "2",
                "source": "agent2",
                "text": "Strong NO evidence",
                "dir": "N",
                "score": 0.73,
                "merged": 0
            }
        ],
        "edges": [
            {
                "from": "1",
                "to": "2",
                "type": "contradicts",
                "strength": 0.8
            }
        ]
    }

    request = TradingDecisionRequest(
        market_id="test-balanced",
        market_question="Will the event happen?",
        current_yes_price=0.50,
        current_no_price=0.50,
        graph_data=json.dumps(graph_json)
    )

    engine = DecisionEngine()
    decision = engine.make_decision(request)

    print(f"\nDecision: {decision.action}")
    print(f"Confidence: {decision.confidence:.2%}")
    print(f"YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)")
    print(f"NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)")
    print(f"\nReasoning:\n{decision.reasoning}")
    print()


def test_strong_no_evidence():
    """Test with strong NO evidence"""
    print("=" * 80)
    print("TEST 4: Strong NO Evidence")
    print("=" * 80)

    graph_text = "YES:Weak yes signal(0.40) NO:Player injured critically(0.95)|Team lost last 5 games(0.88)|Coach suspended(0.82)"

    request = TradingDecisionRequest(
        market_id="test-strong-no",
        market_question="Will the team win?",
        current_yes_price=0.60,
        current_no_price=0.40,
        graph_data=graph_text
    )

    engine = DecisionEngine()
    decision = engine.make_decision(request)

    print(f"\nDecision: {decision.action}")
    print(f"Confidence: {decision.confidence:.2%}")
    print(f"YES Score: {decision.yes_score:.2f} ({decision.yes_count} nodes)")
    print(f"NO Score: {decision.no_score:.2f} ({decision.no_count} nodes)")
    print(f"\nReasoning:\n{decision.reasoning}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DECISION AGENT TEST SUITE")
    print("=" * 80 + "\n")

    try:
        test_json_graph_format()
        test_text_graph_format()
        test_balanced_evidence()
        test_strong_no_evidence()

        print("=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
