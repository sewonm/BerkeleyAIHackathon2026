# Testing Summary - How to Test the Standalone Compression Agent

Quick answers to your questions:

## 1. How do I actually use Redis AI?

### Current Status
Redis vector search is **implemented but NOT integrated** into the main compression pipeline by default. It exists as an optional enhancement.

### How It Works

**Data Storage (all in same Redis database):**
```
chunk:{uuid}                              → Evidence chunk + 384D embedding
claim:{uuid}                              → Claim + 384D embedding
compression:cache:{market_id}:{hash}      → Cached results (1hr TTL)
```

All stored in **single Redis database**, separated by key prefixes (not separate databases).

### Using Redis Vector Search

**Option 1: Test standalone (no code changes)**
```python
from app.compression.redis_similarity import RedisVectorSearch

# Initialize
redis_search = RedisVectorSearch(
    redis_url="redis://localhost:6379",
    embedding_model="sentence-transformer"
)

# Find similar evidence
similar = redis_search.find_similar_chunks(
    text="France won the World Cup",
    market_id="test-market",
    top_k=5,
    similarity_threshold=0.8
)

# Returns: [(chunk_data, similarity_score), ...]
for chunk, score in similar:
    print(f"Similarity: {score:.2f} - {chunk['text']}")
```

**Option 2: Use Redis-enhanced compressor**
```bash
python -m app.compression.demo_advanced_compression --redis
```

This uses `RedisEnhancedCompressor` which integrates vector search.

**Option 3: Compare token-based vs vector-based**
```bash
python -m app.compression.demo_advanced_compression --compare
```

Shows side-by-side comparison of both methods.

### What Redis Provides

1. **Semantic Similarity**
   - Token-based: "France won" vs "French victory" = 14% similar
   - Vector-based: "France won" vs "French victory" = 78% similar

2. **Source Deduplication**
   - Identifies near-duplicate articles from different sources
   - Measures effective source diversity

3. **Better Clustering**
   - Groups semantically similar claims
   - Not fooled by different wording

4. **Caching**
   - Caches compression results for 1 hour
   - Faster repeated requests

### Setup Redis

```bash
# Start Redis Stack (includes vector search)
docker run -d \
  --name redis-vector \
  -p 6379:6379 \
  redis/redis-stack:latest

# Install Python dependencies
pip install redis sentence-transformers numpy

# Set environment variable
export REDIS_URL="redis://localhost:6379"

# Test connection
python -c "from app.compression.redis_similarity import RedisVectorSearch; r = RedisVectorSearch(); print('Enabled:', r.enabled)"
```

Expected output:
```
[RedisVectorSearch] Connected to Redis at redis://localhost:6379
[SentenceTransformer] Loaded all-MiniLM-L6-v2 (dim=384)
Enabled: True
```

---

## 2. How Can I Test Standalone Compression Agent?

### Method 1: Quick Demo (No uAgent required)

**Fastest way - tests core logic directly:**

```bash
python -m app.compression.demo_advanced_compression
```

**What happens:**
1. Loads sample Oscar data from `examples/raw_context/culture_web_context.txt`
2. Runs full compression pipeline
3. Shows metrics in terminal
4. Saves JSON to `examples/outputs/advanced_compression_result.json`

**Expected output:**
```
ADVANCED COMPRESSION PIPELINE DEMO
================================================================================

Loading sample evidence...
Loaded 3 evidence chunks

[AdvancedCompressor] Starting compression for market oscars-2024
[AdvancedCompressor] Evidence chunks: 3
[AdvancedCompressor] Extracted 33 claims
[AdvancedCompressor] Graph: 73 nodes, 119 edges
[AdvancedCompressor] Created 33 consensus items
[AdvancedCompressor] Compression complete: 1.52x

METRICS:
  Raw tokens: 955
  Compressed tokens: 630
  Compression ratio: 1.52x
  Token budget: 3,000

EXTRACTION:
  Total claims extracted: 33
  Claude calls: 3
  Heuristic fallbacks: 0

CONSENSUS:
  Total consensus items: 33
  YES consensus: 18
  NO consensus: 12
  NEUTRAL consensus: 3

GRAPH:
  Nodes: 73
  Edges: 119

COMPRESSED CONTEXT:
============================================================
...
```

### Method 2: Interactive Test Client

**See what the agent does without running it:**

```bash
python test_standalone_compression.py interactive
```

**Features:**
- Choose test scenario (Oscar 2024, France World Cup 2026)
- Set aggressiveness level
- See request that would be sent
- No agent needs to be running

**Example session:**
```
STANDALONE COMPRESSION AGENT TEST CLIENT
================================================================================

Test Scenarios:
  1. Oscar Best Picture 2024 (3 evidence chunks)
  2. France World Cup 2026 (4 evidence chunks)
  3. Custom test (enter your own data)
  4. Aggressiveness test (same data, different compression levels)
  q. Quit

Select option: 1

Compression aggressiveness (0.0-1.0, default 0.5): 0.7

✅ Selected scenario: Will Oppenheimer win Best Picture at the 2024 Oscars?
   Evidence chunks: 3
   Current YES price: 0.85
   Aggressiveness: 0.7

📤 Request that would be sent:
{
  "market_id": "oscars-2024",
  "market_question": "Will Oppenheimer win Best Picture...",
  "evidence_chunks": [...],
  "aggressiveness": 0.7
}
```

### Method 3: Full uAgent Test

**Test the actual deployable agent:**

**Terminal 1 - Start the agent:**
```bash
cd uagents_deploy
python standalone_compression_agent.py
```

Expected output:
```
[standalone_compression_agent] Standalone Compression Agent started!
Address: agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x9m0n5j6h3k2l4m7n9p8
Mode: Graph-Consensus Compression
Ready to compress evidence contexts
Claude extraction: ENABLED
```

**Terminal 2 - Send test message:**
```bash
python test_standalone_compression.py
```

This sends actual uAgent messages and waits for responses.

### Method 4: Run Unit Tests

**Verify all components work:**

```bash
pytest tests/test_advanced_compression.py -v
```

**All 10 tests should pass:**
```
test_heuristic_extractor_works ✓
test_compressor_works_without_redis ✓
test_compressor_works_without_claude ✓
test_consensus_clustering_merges_similar_claims ✓
test_consensus_does_not_merge_unrelated_claims ✓
test_evidence_graph_has_nodes_and_edges ✓
test_compression_ratio_greater_than_one ✓
test_compressed_context_not_empty ✓
test_information_value_scoring ✓
test_contradictions_identified ✓

========== 10 passed in 2.34s ==========
```

---

## Testing With vs Without Redis

### Run Comparison Test

```bash
python -m app.compression.demo_advanced_compression --compare
```

**What it does:**
1. Runs standard (token-based) compression
2. Runs Redis-enhanced (vector-based) compression
3. Shows side-by-side comparison

**Expected output:**
```
COMPRESSION COMPARISON: Token-Based vs Redis Vector Search
================================================================================

Running BOTH compression methods on the same evidence...

--------------------------------------------------------------------------------
1. STANDARD COMPRESSION (Token-Based Clustering)
--------------------------------------------------------------------------------
[Runs compression...]

--------------------------------------------------------------------------------
2. REDIS-ENHANCED COMPRESSION (Vector-Based Clustering)
--------------------------------------------------------------------------------
[Runs compression...]

COMPARISON SUMMARY
================================================================================

COMPRESSION RATIO:
  Standard:       1.52x
  Redis-Enhanced: 1.68x
  Improvement:    +10.5%

CONSENSUS ITEMS:
  Standard:       33
  Redis-Enhanced: 28

CLUSTERING METHOD:
  Standard:       token_jaccard
  Redis-Enhanced: redis_vector

CACHE HITS:
  Standard:       0 hits, 1 misses
  Redis-Enhanced: 0 hits, 1 misses  (first run, cache empty)
```

---

## Verification Checklist

Run through this to verify everything works:

### ✅ 1. Core Compression Works
```bash
python -m app.compression.demo_advanced_compression
# Should complete successfully and save JSON output
```

### ✅ 2. Tests Pass
```bash
pytest tests/test_advanced_compression.py -v
# All 10 tests should pass
```

### ✅ 3. Interactive Client Works
```bash
python test_standalone_compression.py interactive
# Should show menu and scenarios
```

### ✅ 4. Standalone Agent Starts
```bash
cd uagents_deploy && python standalone_compression_agent.py
# Should start without errors
```

### ✅ 5. Redis Integration (Optional)
```bash
# Start Redis
docker run -d --name redis-vector -p 6379:6379 redis/redis-stack:latest

# Test Redis connection
python -c "from app.compression.redis_similarity import RedisVectorSearch; r = RedisVectorSearch(); print('Redis:', 'ENABLED' if r.enabled else 'DISABLED')"

# Run with Redis
python -m app.compression.demo_advanced_compression --redis
# Should show "Redis enabled: True"
```

---

## Output Files

After running tests, check these files:

1. **Compression result:**
   ```
   examples/outputs/advanced_compression_result.json
   ```
   Contains full compression output (graph, claims, metrics)

2. **Test output:**
   ```
   test_compression_output_YYYYMMDD_HHMMSS.json
   ```
   Created by interactive test client

3. **Logs:**
   - Terminal output shows compression steps
   - Redis logs: `docker logs redis-vector`

---

## Common Test Scenarios

### Scenario 1: Oscar Best Picture 2024
```python
Market: "Will Oppenheimer win Best Picture at the 2024 Oscars?"
Current YES price: 0.85
Evidence: 3 chunks about awards season dominance
Expected: Strong YES consensus (18 items)
```

### Scenario 2: France World Cup 2026
```python
Market: "Will France win the 2026 FIFA World Cup?"
Current YES price: 0.18
Evidence: 4 chunks (mixed signals - talent vs injuries)
Expected: Balanced YES/NO consensus
```

### Scenario 3: Custom Aggressiveness Test
```python
Same evidence, different aggressiveness levels:
- 0.3 (low): Keep most items (e.g., 33 consensus items)
- 0.5 (moderate): Balanced filtering (e.g., 28 items)
- 0.8 (high): Only top items (e.g., 15 items)
```

---

## Debugging

### If compression fails:

1. **Check sample data exists:**
   ```bash
   ls examples/raw_context/culture_web_context.txt
   ```

2. **Run with verbose logging:**
   ```bash
   python -m app.compression.demo_advanced_compression 2>&1 | tee compression.log
   ```

3. **Test individual components:**
   ```bash
   pytest tests/test_advanced_compression.py::test_heuristic_extractor_works -v
   ```

### If Redis fails:

1. **Check Redis is running:**
   ```bash
   docker ps | grep redis-vector
   redis-cli ping  # Should return PONG
   ```

2. **Check Redis indexes:**
   ```bash
   redis-cli
   FT._LIST  # Should show idx:chunks and idx:claims
   ```

3. **Clear Redis data:**
   ```bash
   redis-cli FLUSHDB
   ```

---

## Summary

**To test the standalone compression agent:**

1. **Quickest:** `python -m app.compression.demo_advanced_compression`
2. **Interactive:** `python test_standalone_compression.py interactive`
3. **Full uAgent:** Start agent, then run test client
4. **With Redis:** Add `--redis` flag to demo command

**Redis is OPTIONAL** - the system works perfectly without it. It's just an enhancement for semantic similarity.

**All in same database** - Redis uses key prefixes to separate data types, not separate databases.

For more details, see:
- **Quick Start:** `QUICK_START_GUIDE.md`
- **Redis Details:** `REDIS_INTEGRATION.md`
- **Deployment:** `AGENTVERSE_DEPLOYMENT_GUIDE.md`
