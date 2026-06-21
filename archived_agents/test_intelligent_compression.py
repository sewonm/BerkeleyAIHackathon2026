#!/usr/bin/env python3
"""Test intelligent compression with real noisy data"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from intelligent_compressor import IntelligentCompressor

def test_intelligent_compression():
    """Test with realistic noisy data"""

    print("=" * 80)
    print("INTELLIGENT COMPRESSION TEST - Real Noisy Data")
    print("=" * 80)
    print()

    # Create test evidence chunks with REAL noisy data formats
    evidence_chunks = [
        {
            # ESPN-style JSON (sports_video)
            "source_type": "sports_video",
            "text": '{"game": {"status": "final", "competitors": [{"team": "France", "score": 2}, {"team": "Brazil", "score": 1}]}, "injuries": [{"player": "Pogba", "status": "questionable with ankle injury"}, {"player": "Varane", "status": "healthy"}], "odds": {"favorite": "France", "line": "-150", "implied_prob": 0.60}}',
            "source_url": "https://espn.com/soccer/match",
            "confidence": 0.85
        },
        {
            # Scraped HTML (noisy Browserbase scrape)
            "source_type": "sports_video",
            "text": '<html><body><div class="content"><h1>France vs Brazil Match Report</h1><p>France dominated the match with a convincing 2-1 victory. Mbappe scored twice in the second half, showing exceptional form against a struggling Brazilian defense.</p><p>The French team has now won 4 out of their last 5 matches against top-ranked opponents, cementing their position as tournament favorites.</p></div></body></html>',
            "source_url": "https://sportsnews.com/france-brazil",
            "confidence": 0.70
        },
        {
            # Kalshi-style market data (financial_research)
            "source_type": "financial_research",
            "text": '{"market_id": "france-wc-2026", "yes_price": 0.62, "no_price": 0.38, "volume": 12450, "last_trade_price": 0.63, "price_movement_24h": 0.05}',
            "source_url": "https://kalshi.com/markets/france-wc",
            "confidence": 0.80
        },
        {
            # Plain text chunk
            "source_type": "culture_web",
            "text": "However, concerns remain about France's midfield depth. With Pogba nursing an ankle injury and Kanté recovering from surgery, the team may struggle in high-pressure situations. Historical data shows that teams with injury concerns in key positions have a 35% lower chance of tournament success.",
            "source_url": "https://sportsanalysis.com/france-concerns",
            "confidence": 0.75
        },
        {
            # More noisy JSON
            "source_type": "sports_video",
            "text": '{"recent_form": [{"match": "France vs Argentina", "result": "W", "score": "3-2"}, {"match": "France vs Germany", "result": "W", "score": "2-0"}, {"match": "France vs Italy", "result": "L", "score": "1-2"}], "stats": {"goals_for": 15, "goals_against": 8, "clean_sheets": 3}}',
            "source_url": "https://stats.espn.com/france",
            "confidence": 0.80
        }
    ]

    print(f"INPUT: {len(evidence_chunks)} evidence chunks with noisy data")
    print()
    for i, chunk in enumerate(evidence_chunks, 1):
        print(f"Chunk {i} ({chunk['source_type']}):")
        preview = chunk['text'][:100].replace('\n', ' ')
        print(f"  {preview}...")
        print()

    # Create compressor
    compressor = IntelligentCompressor()

    # Compress
    print("=" * 80)
    print("COMPRESSING...")
    print("=" * 80)
    print()

    compressed_text, metrics = compressor.compress(
        market_question="Will France win the World Cup 2026?",
        protected_terms=["France", "World Cup", "2026", "Mbappe", "Pogba"],
        evidence_chunks=evidence_chunks,
        token_budget=150,
        output_format="text"
    )

    print("COMPRESSED OUTPUT (Text Format):")
    print("-" * 80)
    print(compressed_text)
    print("-" * 80)
    print()

    print("METRICS:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print()

    # Also test JSON output
    compressed_json, metrics_json = compressor.compress(
        market_question="Will France win the World Cup 2026?",
        protected_terms=["France", "World Cup", "2026", "Mbappe", "Pogba"],
        evidence_chunks=evidence_chunks,
        token_budget=200,
        output_format="json"
    )

    print("COMPRESSED OUTPUT (JSON Format):")
    print("-" * 80)
    import json
    graph = json.loads(compressed_json)
    print(json.dumps(graph, indent=2))
    print("-" * 80)
    print()

    # Validation
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print()

    checks = []

    # Check 1: Compression achieved
    if metrics['compression_ratio'] >= 1.5:
        checks.append(f"✅ Compression ratio: {metrics['compression_ratio']}x (good!)")
    else:
        checks.append(f"⚠️  Compression ratio: {metrics['compression_ratio']}x (low)")

    # Check 2: Facts extracted from noisy data
    if metrics['facts_extracted'] >= 10:
        checks.append(f"✅ Facts extracted: {metrics['facts_extracted']} (parsed noisy data!)")
    else:
        checks.append(f"⚠️  Facts extracted: {metrics['facts_extracted']} (too few)")

    # Check 3: Market question present
    if "Will France win" in compressed_text:
        checks.append("✅ Market question in output")
    else:
        checks.append("❌ Market question missing")

    # Check 4: Supporting facts present
    if metrics['supporting_facts'] > 0:
        checks.append(f"✅ Supporting facts: {metrics['supporting_facts']}")
    else:
        checks.append("⚠️  No supporting facts")

    # Check 5: Contradicting facts present
    if metrics['contradicting_facts'] > 0:
        checks.append(f"✅ Contradicting facts: {metrics['contradicting_facts']}")
    else:
        checks.append("⚠️  No contradicting facts")

    # Check 6: JSON/HTML parsed
    if metrics['json_parses'] > 0:
        checks.append(f"✅ JSON parsed: {metrics['json_parses']} chunks")
    else:
        checks.append("⚠️  No JSON parsing")

    if metrics['html_parses'] > 0:
        checks.append(f"✅ HTML parsed: {metrics['html_parses']} chunks")
    else:
        checks.append("⚠️  No HTML parsing")

    for check in checks:
        print(check)
    print()

    # Overall success
    success = (
        metrics['compression_ratio'] >= 1.5 and
        metrics['facts_extracted'] >= 10 and
        metrics['supporting_facts'] > 0 and
        metrics['contradicting_facts'] > 0 and
        (metrics['json_parses'] + metrics['html_parses']) > 0
    )

    if success:
        print("✅ ✅ ✅ INTELLIGENT COMPRESSION SUCCESSFUL! ✅ ✅ ✅")
        print()
        print("Key achievements:")
        print(f"  - Parsed {metrics['json_parses']} JSON chunks")
        print(f"  - Parsed {metrics['html_parses']} HTML chunks")
        print(f"  - Extracted {metrics['facts_extracted']} facts from noisy data")
        print(f"  - After dedup: {metrics['facts_after_dedup']} unique facts")
        print(f"  - Final output: {metrics['facts_final']} high-quality facts")
        print(f"  - Compression: {metrics['raw_tokens']} → {metrics['compressed_tokens']} tokens ({metrics['compression_ratio']}x)")
        print(f"  - Market-centric: {metrics['supporting_facts']} YES, {metrics['contradicting_facts']} NO")
        return True
    else:
        print("❌ Test failed - compression needs improvement")
        return False


if __name__ == "__main__":
    success = test_intelligent_compression()
    sys.exit(0 if success else 1)
