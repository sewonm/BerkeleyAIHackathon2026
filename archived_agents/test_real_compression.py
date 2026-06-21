#!/usr/bin/env python3
"""
Test real compression - verify it actually reduces token count
"""

import sys
import os
import json

# Add the uagents_deploy directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from real_compressor import RealCompressor


def test_real_compression():
    """Test that compression actually reduces tokens"""

    print("=" * 80)
    print("REAL COMPRESSION TEST")
    print("=" * 80)
    print()

    # Create test data with LOTS of redundancy (real-world scenario)
    evidence_chunks = [
        {
            "chunk_id": "1",
            "source_agent": "sports_video_agent",
            "text": """France defeated Brazil 2-1 in a thrilling match yesterday.
                The match was very exciting and competitive. The game was intense.
                Mbappe scored twice in the second half, showing exceptional form.
                Mbappe was in great shape and played very well. Mbappe's performance
                was outstanding. The French defense held strong against Brazil's attacks.
                The defense was solid and resilient. France's defensive line was excellent."""
        },
        {
            "chunk_id": "2",
            "source_agent": "odds_agent",
            "text": """Current betting odds favor France at 58% implied probability.
                The odds are 58% for France to win. The betting markets show 58%.
                Odds have shifted 5% in favor over the past week. The market has
                moved 5% towards France. There has been a 5 percent shift in the odds."""
        },
        {
            "chunk_id": "3",
            "source_agent": "news_agent",
            "text": """However, France struggled in their last friendly match, barely
                winning 1-0 against a lower-ranked team. The friendly was not impressive.
                France didn't play well in the friendly. Key midfielder Pogba is nursing
                a minor injury. Pogba has a small injury issue. Pogba is questionable."""
        }
    ]

    # Count input tokens
    input_text = " ".join(chunk["text"] for chunk in evidence_chunks)
    input_tokens = len(input_text.split())

    print("INPUT DATA:")
    print(f"  Chunks: {len(evidence_chunks)}")
    print(f"  Total characters: {len(input_text)}")
    print(f"  Total tokens (word count): {input_tokens}")
    print()

    # Test with different token budgets
    budgets = [100, 150, 200]

    for budget in budgets:
        print("-" * 80)
        print(f"TESTING WITH TOKEN BUDGET: {budget}")
        print("-" * 80)

        compressor = RealCompressor(similarity_threshold=0.4)
        output, metrics = compressor.compress(
            evidence_chunks=evidence_chunks,
            market_question="Will France win the World Cup 2026?",
            token_budget=budget
        )

        print()
        print("COMPRESSION METRICS:")
        print(f"  Raw tokens: {metrics['raw_tokens']}")
        print(f"  Compressed tokens: {metrics['compressed_tokens']}")
        print(f"  Compression ratio: {metrics['compression_ratio']}x")
        print(f"  Claims extracted: {metrics['claims_extracted']}")
        print(f"  After deduplication: {metrics['claims_after_dedup']}")
        print(f"  After clustering: {metrics['claims_after_clustering']}")
        print(f"  Final claims: {metrics['final_claims']}")
        print(f"  Edges: {metrics['edges']}")
        print(f"  Budget used: {metrics['budget_used_pct']}%")
        print()

        print("COMPRESSED OUTPUT:")
        print(json.dumps(output, indent=2))
        print()

        # Verify compression actually happened
        if metrics['compression_ratio'] > 1.0:
            print(f"✅ SUCCESS: Achieved {metrics['compression_ratio']}x compression!")
        else:
            print(f"❌ FAIL: No compression (ratio {metrics['compression_ratio']}x)")

        print()

    # Final validation
    print("=" * 80)
    print("FINAL VALIDATION")
    print("=" * 80)

    final_compressor = RealCompressor(similarity_threshold=0.4)
    final_output, final_metrics = final_compressor.compress(
        evidence_chunks=evidence_chunks,
        market_question="Will France win the World Cup 2026?",
        token_budget=150
    )

    print()
    print("Key Information Preserved:")
    print(f"  Total claims: {len(final_output['claims'])}")
    print(f"  YES claims: {len(final_output['yes'])}")
    print(f"  NO claims: {len(final_output['no'])}")
    print()

    print("Top YES Evidence:")
    for idx in final_output['yes'][:3]:
        claim = final_output['claims'][idx]
        # claim format: [text, dir_code, val, shift]
        print(f"  - {claim[0]} (value: {claim[2]}, shift: {claim[3]})")
    print()

    print("Top NO Evidence:")
    for idx in final_output['no'][:3]:
        claim = final_output['claims'][idx]
        print(f"  - {claim[0]} (value: {claim[2]}, shift: {claim[3]})")
    print()

    # Check if we achieved real compression
    success = final_metrics['compression_ratio'] >= 2.0

    if success:
        print("✅ ✅ ✅ REAL COMPRESSION ACHIEVED! ✅ ✅ ✅")
        print(f"Reduced {final_metrics['raw_tokens']} tokens to {final_metrics['compressed_tokens']} tokens")
        print(f"Compression ratio: {final_metrics['compression_ratio']}x")
        print()
        return True
    else:
        print("❌ ❌ ❌ COMPRESSION FAILED ❌ ❌ ❌")
        print(f"Only achieved {final_metrics['compression_ratio']}x compression")
        print()
        return False


if __name__ == "__main__":
    success = test_real_compression()
    sys.exit(0 if success else 1)
