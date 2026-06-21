#!/usr/bin/env python3
"""
Test the intelligent compression agent with real ESPN HTML data
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from intelligent_compressor import IntelligentCompressor


def main():
    print("=" * 80)
    print("TESTING INTELLIGENT COMPRESSION WITH ESPN HTML DATA")
    print("=" * 80)
    print()

    # Load test input
    with open('test_espn_input.json', 'r') as f:
        test_data = json.load(f)

    print(f"INPUT:")
    print(f"  Market: {test_data['market_question']}")
    print(f"  Protected terms: {test_data['protected_terms']}")
    print(f"  Evidence chunks: {len(test_data['evidence_chunks'])}")
    print(f"  Raw text length: {len(test_data['evidence_chunks'][0]['text'])} chars")
    print(f"  Token budget: {test_data['token_budget']}")
    print()

    # Create compressor
    compressor = IntelligentCompressor()

    # Compress
    print("=" * 80)
    print("COMPRESSING...")
    print("=" * 80)
    print()

    compressed_output, metrics = compressor.compress(
        market_question=test_data['market_question'],
        protected_terms=test_data['protected_terms'],
        evidence_chunks=test_data['evidence_chunks'],
        token_budget=test_data['token_budget'],
        output_format=test_data['output_format']
    )

    # Show results
    print("COMPRESSED OUTPUT (JSON GRAPH):")
    print("-" * 80)

    # Pretty print JSON if output format is json
    if test_data.get('output_format') == 'json':
        try:
            graph = json.loads(compressed_output)
            print(json.dumps(graph, indent=2))
        except:
            print(compressed_output)
    else:
        print(compressed_output)

    print("-" * 80)
    print()

    print("METRICS:")
    print(f"  ✅ HTML parsed: {metrics['html_parses']} chunks")
    print(f"  ✅ Text parsed: {metrics['text_parses']} chunks")
    print(f"  ✅ Facts extracted: {metrics['facts_extracted']}")
    print(f"  ✅ After deduplication: {metrics['facts_after_dedup']}")
    print(f"  ✅ Final facts: {metrics['facts_final']}")
    print()
    print(f"  📊 Supporting facts (YES): {metrics['supporting_facts']}")
    print(f"  📊 Contradicting facts (NO): {metrics['contradicting_facts']}")
    print(f"  📊 Neutral facts: {metrics['neutral_facts']}")
    print()
    print(f"  🗜️ Raw tokens: {metrics['raw_tokens']}")
    print(f"  🗜️ Compressed tokens: {metrics['compressed_tokens']}")
    print(f"  🗜️ Compression ratio: {metrics['compression_ratio']}x")
    print()

    # Expected facts about France in graph
    print("=" * 80)
    print("VALIDATION - Expected France Facts in Graph:")
    print("=" * 80)
    expected_facts = [
        "France ranked #1",
        "Kylian Mbappé scored twice",
        "France beat Brazil 2-1",
        "Going for third World Cup title",
        "Won 4 of last 5 matches",
        "Paul Pogba loss mentioned",
    ]

    # Check if facts are in the output
    for expected in expected_facts:
        found = any(expected.lower() in compressed_output.lower().split('\n')[i] for i in range(min(10, len(compressed_output.split('\n')))))
        status = "✅" if expected.lower() in compressed_output.lower() else "⚠️"
        print(f"{status} {expected}")
    print()

    # Overall success
    if metrics['compression_ratio'] >= 3.0 and metrics['facts_extracted'] >= 10:
        print("✅ ✅ ✅ ESPN COMPRESSION TEST SUCCESSFUL! ✅ ✅ ✅")
        print()
        print("The agent successfully:")
        print(f"  - Parsed noisy ESPN HTML ({len(test_data['evidence_chunks'][0]['text'])} chars)")
        print(f"  - Extracted {metrics['facts_extracted']} clean facts")
        print(f"  - Built market-centric graph around: {test_data['market_question']}")
        print(f"  - Achieved {metrics['compression_ratio']}x compression")
        print(f"  - Identified {metrics['supporting_facts']} supporting and {metrics['contradicting_facts']} contradicting facts")
        return True
    else:
        print("⚠️ Compression could be improved")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
