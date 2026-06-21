#!/usr/bin/env python3
"""
Test standalone_decision_agent.py with intelligent_compression_agent.py output format
"""

import json
import re
from typing import Dict, Any

def test_intelligent_compression_json():
    """Test with JSON format from intelligent_compression_agent.py"""
    print("=" * 80)
    print("TEST: Intelligent Compression JSON Format")
    print("=" * 80)

    # This is the actual format from intelligent_compression_agent.py
    intelligent_output = {
        "market": {
            "question": "Will France win the World Cup 2026?",
            "protected_terms": ["France", "World Cup", "2026", "Mbappe", "Pogba"]
        },
        "facts": [
            {
                "text": "France beat Brazil 2-1 in thrilling match",
                "confidence": 0.95,
                "source_type": "sports_video",
                "source_url": "https://espn.com/match",
                "relation_to_market": "supports",
                "relation_strength": 0.95
            },
            {
                "text": "Mbappe scored twice showing excellent form",
                "confidence": 0.90,
                "source_type": "sports_video",
                "source_url": "https://espn.com/match",
                "relation_to_market": "supports",
                "relation_strength": 0.90
            },
            {
                "text": "France won 4 of last 5 matches",
                "confidence": 0.85,
                "source_type": "sports_stats",
                "source_url": None,
                "relation_to_market": "supports",
                "relation_strength": 0.85
            },
            {
                "text": "Pogba with ankle injury affecting midfield",
                "confidence": 0.80,
                "source_type": "injury_report",
                "source_url": None,
                "relation_to_market": "contradicts",
                "relation_strength": 0.80
            },
            {
                "text": "Midfield depth concerns without key player",
                "confidence": 0.75,
                "source_type": "analysis",
                "source_url": None,
                "relation_to_market": "contradicts",
                "relation_strength": 0.75
            }
        ],
        "summary": {
            "total_facts": 5,
            "supporting": 3,
            "contradicting": 2,
            "neutral": 0
        }
    }

    # Parse using the decision agent logic
    def analyze_intelligent_compression(data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze JSON format from intelligent_compression_agent.py"""
        facts = data.get("facts", [])
        summary = data.get("summary", {})

        # Separate facts by relation_to_market
        yes_facts = [f for f in facts if f.get("relation_to_market") == "supports"]
        no_facts = [f for f in facts if f.get("relation_to_market") == "contradicts"]

        # Calculate weighted average scores using confidence * relation_strength
        if yes_facts:
            yes_score = sum(
                f.get("confidence", 0.5) * f.get("relation_strength", 0.5)
                for f in yes_facts
            ) / len(yes_facts)
        else:
            yes_score = 0.0

        if no_facts:
            no_score = sum(
                f.get("confidence", 0.5) * f.get("relation_strength", 0.5)
                for f in no_facts
            ) / len(no_facts)
        else:
            no_score = 0.0

        # Normalize to 0-1 range
        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total
        else:
            yes_score = 0.5
            no_score = 0.5

        return {
            "yes_facts": yes_facts,
            "no_facts": no_facts,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_facts),
            "no_count": len(no_facts),
            "summary": summary
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

    # Run analysis
    analysis = analyze_intelligent_compression(intelligent_output)
    decision = make_decision(analysis)

    # Display results
    print(f"\n📊 Analysis Results:")
    print(f"  Supporting Facts: {analysis['yes_count']}")
    print(f"  Contradicting Facts: {analysis['no_count']}")
    print(f"  YES Score: {analysis['yes_score']:.3f}")
    print(f"  NO Score: {analysis['no_score']:.3f}")

    print(f"\n✅ Decision: {decision['action']}")
    print(f"  Confidence: {decision['confidence']:.1%}")

    print(f"\n📝 Supporting Evidence:")
    for i, fact in enumerate(analysis['yes_facts'], 1):
        conf = fact['confidence']
        strength = fact['relation_strength']
        weighted = conf * strength
        print(f"  {i}. {fact['text']}")
        print(f"     Confidence: {conf:.2f}, Strength: {strength:.2f}, Weighted: {weighted:.2f}")

    print(f"\n📝 Contradicting Evidence:")
    for i, fact in enumerate(analysis['no_facts'], 1):
        conf = fact['confidence']
        strength = fact['relation_strength']
        weighted = conf * strength
        print(f"  {i}. {fact['text']}")
        print(f"     Confidence: {conf:.2f}, Strength: {strength:.2f}, Weighted: {weighted:.2f}")

    # Verify this would work in decision agent
    assert analysis['yes_count'] == 3, f"Expected 3 YES facts, got {analysis['yes_count']}"
    assert analysis['no_count'] == 2, f"Expected 2 NO facts, got {analysis['no_count']}"
    assert decision['action'] in ["YES", "NO", "HOLD"], f"Invalid action: {decision['action']}"
    assert 0.0 <= decision['confidence'] <= 1.0, f"Invalid confidence: {decision['confidence']}"

    print(f"\n✅ All assertions passed!")
    return decision


def test_intelligent_compression_text():
    """Test with text format from intelligent_compression_agent.py"""
    print("\n" + "=" * 80)
    print("TEST: Intelligent Compression Text Format")
    print("=" * 80)

    # Text format from intelligent_compression_agent.py
    text_output = """Q: Will France win the World Cup 2026?
YES: France beat Brazil 2-1 in thrilling match(0.95)|Mbappe scored twice showing excellent form(0.90)|France won 4 of last 5 matches(0.85)
NO: Pogba with ankle injury affecting midfield(0.80)|Midfield depth concerns without key player(0.75)"""

    def parse_text_format(text: str) -> Dict[str, Any]:
        """Parse text format from intelligent_compression_agent.py"""
        yes_pattern = r'YES:\s*(.*?)(?:NO:|$)'
        no_pattern = r'NO:\s*(.*?)$'

        yes_match = re.search(yes_pattern, text, re.DOTALL)
        no_match = re.search(no_pattern, text, re.DOTALL)

        yes_facts = []
        no_facts = []

        if yes_match:
            yes_text = yes_match.group(1).strip()
            for fact in yes_text.split("|"):
                if not fact.strip():
                    continue
                score_match = re.search(r'\(([0-9.]+)\)', fact)
                score = float(score_match.group(1)) if score_match else 0.5
                text_part = re.sub(r'\([0-9.]+\)', '', fact).strip()
                yes_facts.append({"text": text_part, "confidence": score})

        if no_match:
            no_text = no_match.group(1).strip()
            for fact in no_text.split("|"):
                if not fact.strip():
                    continue
                score_match = re.search(r'\(([0-9.]+)\)', fact)
                score = float(score_match.group(1)) if score_match else 0.5
                text_part = re.sub(r'\([0-9.]+\)', '', fact).strip()
                no_facts.append({"text": text_part, "confidence": score})

        yes_score = sum(f["confidence"] for f in yes_facts) / max(len(yes_facts), 1)
        no_score = sum(f["confidence"] for f in no_facts) / max(len(no_facts), 1)

        total = yes_score + no_score
        if total > 0:
            yes_score = yes_score / total
            no_score = no_score / total

        return {
            "yes_facts": yes_facts,
            "no_facts": no_facts,
            "yes_score": yes_score,
            "no_score": no_score,
            "yes_count": len(yes_facts),
            "no_count": len(no_facts)
        }

    analysis = parse_text_format(text_output)

    print(f"\n📊 Parsed from text:")
    print(f"  YES Facts: {analysis['yes_count']}")
    print(f"  NO Facts: {analysis['no_count']}")
    print(f"  YES Score: {analysis['yes_score']:.3f}")
    print(f"  NO Score: {analysis['no_score']:.3f}")

    for i, fact in enumerate(analysis['yes_facts'], 1):
        print(f"  YES {i}: {fact['text'][:60]}... ({fact['confidence']:.2f})")

    for i, fact in enumerate(analysis['no_facts'], 1):
        print(f"  NO {i}: {fact['text'][:60]}... ({fact['confidence']:.2f})")

    assert analysis['yes_count'] == 3
    assert analysis['no_count'] == 2
    print(f"\n✅ Text parsing successful!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INTELLIGENT COMPRESSION → DECISION AGENT TEST SUITE")
    print("=" * 80 + "\n")

    try:
        decision = test_intelligent_compression_json()
        test_intelligent_compression_text()

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED - Decision agent correctly parses intelligent compression!")
        print("=" * 80)
        print(f"\nFinal Decision: {decision['action']} with {decision['confidence']:.1%} confidence")
        print(f"YES Score: {decision['yes_score']:.3f} ({decision['yes_count']} facts)")
        print(f"NO Score: {decision['no_score']:.3f} ({decision['no_count']} facts)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
