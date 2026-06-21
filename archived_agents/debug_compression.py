#!/usr/bin/env python3
"""Debug compression to see why clustering isn't working"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uagents_deploy'))

from real_compressor import RealCompressor

evidence_chunks = [
    {
        "chunk_id": "1",
        "source_agent": "test",
        "text": """France defeated Brazil 2-1. France beat Brazil 2-1.
        France won against Brazil with a 2-1 score."""
    }
]

compressor = RealCompressor(similarity_threshold=0.4)
sentences = compressor._parse_all_sentences(evidence_chunks)

print("PARSED SENTENCES:")
for i, s in enumerate(sentences):
    print(f"{i}: {s.text}")
    print(f"   Tokens: {set(s.text.lower().split())}")
print()

unique = compressor._deduplicate_exact(sentences)
print(f"AFTER EXACT DEDUP: {len(sentences)} -> {len(unique)}")
for i, s in enumerate(unique):
    print(f"{i}: {s.text}")
print()

clusters = compressor._cluster_similar(unique)
print(f"AFTER CLUSTERING: {len(unique)} -> {len(clusters)} clusters")
for i, cluster in enumerate(clusters):
    print(f"Cluster {i} (size {len(cluster)}):")
    for s in cluster:
        print(f"  - {s.text}")
print()
