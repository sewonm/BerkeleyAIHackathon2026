# Quick Start Guide - Testing Your Compression Agent

This guide shows you **3 easy ways** to test the standalone compression agent.

---

## Method 1: Interactive Test (Easiest - No Setup Required)

Run the interactive test client to see what the agent does:

```bash
python test_standalone_compression.py interactive
```

**What you'll see:**
- Menu with test scenarios (Oscar 2024, France World Cup 2026)
- Shows the request that would be sent
- Demonstrates different aggressiveness levels
- No agent needs to be running

**Example:**
```
Select option: 1
Compression aggressiveness (0.0-1.0, default 0.5): 0.7

✅ Selected scenario: Will Oppenheimer win Best Picture at the 2024 Oscars?
   Evidence chunks: 3
   Current YES price: 0.85
   Aggressiveness: 0.7
```

---

## Method 2: Run Demo Script (Tests Core Logic)

Test the compression logic directly without uAgents:

```bash
# Standard compression (token-based clustering)
python -m app.compression.demo_advanced_compression

# With Redis vector search
python -m app.compression.demo_advanced_compression --redis

# Compare both methods side-by-side
python -m app.compression.demo_advanced_compression --compare
```

**What you'll see:**
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

Full result saved to: examples/outputs/advanced_compression_result.json
```

---

## Method 3: Run Standalone uAgent (Full Agent Test)

Test the actual Agentverse-deployable agent:

**Terminal 1 - Start the agent:**
```bash
cd uagents_deploy
python standalone_compression_agent.py
```

**Terminal 2 - Send it a test message:**
```bash
python test_standalone_compression.py
```

*(This requires both terminals running and sends actual uAgent messages)*

---

## Understanding Redis Integration

### What is Redis doing?

Redis provides **semantic similarity search** instead of just token matching.

**Example:**
- **Without Redis** (token-based):
  - "France won the match" vs "French victory in the game"
  - Token similarity: **14%** (only "the" matches)

- **With Redis** (vector-based):
  - "France won the match" vs "French victory in the game"
  - Semantic similarity: **78%** (understands same meaning!)

### How to enable Redis?

**Step 1: Start Redis**
```bash
docker run -d --name redis-vector -p 6379:6379 redis/redis-stack:latest
```

**Step 2: Install dependencies**
```bash
pip install redis sentence-transformers numpy
```

**Step 3: Set environment variable**
```bash
export REDIS_URL="redis://localhost:6379"
```

**Step 4: Run with Redis**
```bash
python -m app.compression.demo_advanced_compression --redis
```

### Does the system NEED Redis?

**No!** The compression agent works perfectly without Redis. It's **optional** for quality improvements.

**Use Redis when:**
- ✅ Processing large volumes of evidence
- ✅ Evidence contains paraphrased information
- ✅ Need source deduplication
- ✅ Quality > Speed

**Skip Redis when:**
- ✅ Quick hackathon/demo
- ✅ Small evidence sets
- ✅ Speed is critical
- ✅ No Redis infrastructure

---

## How to Test Each Component

### 1. Test Compression Agent

```bash
# Without Redis
python -m app.compression.demo_advanced_compression

# With Redis
python -m app.compression.demo_advanced_compression --redis
```

### 2. Test Decision Agent

```bash
# Start the agent
cd uagents_deploy
python standalone_decision_agent.py
```

Then create a test file:
```python
# test_decision.py
from uagents_deploy.standalone_decision_agent import TradingDecisionRequest

request = TradingDecisionRequest(
    market_id="test-market",
    market_question="Will France win the World Cup?",
    resolution_criteria="...",
    current_yes_price=0.18,
    current_no_price=0.82,
    compressed_context="<paste compressed output here>",
    max_position_size=100.0,
    risk_tolerance="moderate"
)

# Send to agent...
```

### 3. Test Kalshi Agent

```bash
# Set credentials
export KALSHI_EMAIL=your_email@example.com
export KALSHI_PASSWORD=your_password
export KALSHI_USE_DEMO=true  # Use demo mode for testing

# Start the agent
cd uagents_deploy
python standalone_kalshi_agent.py
```

---

## Quick Commands Reference

```bash
# Test compression (standard)
python -m app.compression.demo_advanced_compression

# Test compression (with Redis)
python -m app.compression.demo_advanced_compression --redis

# Compare token-based vs vector-based
python -m app.compression.demo_advanced_compression --compare

# Interactive test (no agent needed)
python test_standalone_compression.py interactive

# Run all tests
pytest tests/test_advanced_compression.py -v

# Start standalone compression agent
cd uagents_deploy && python standalone_compression_agent.py

# Start standalone decision agent
cd uagents_deploy && python standalone_decision_agent.py

# Start standalone Kalshi agent
cd uagents_deploy && python standalone_kalshi_agent.py

# Start Redis (if needed)
docker run -d --name redis-vector -p 6379:6379 redis/redis-stack:latest

# Check Redis status
redis-cli ping  # Should return PONG
```

---

## Environment Variables

| Variable | Required | Purpose | Default |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Optional | Claude-based reasoning | Fallback to heuristics |
| `REDIS_URL` | Optional | Vector search | System works without it |
| `KALSHI_EMAIL` | Yes* | Kalshi API auth | - |
| `KALSHI_PASSWORD` | Yes* | Kalshi API auth | - |
| `KALSHI_USE_DEMO` | No | Use demo API | `true` |

\* Only required for Kalshi Execution Agent

---

## Expected Output

### Compression Demo Output:
```
METRICS:
  Raw tokens: 955
  Compressed tokens: 630
  Compression ratio: 1.52x

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
COMPRESSED EVIDENCE CONTEXT
============================================================

MARKET:
Will 'Stellar Dreams' win Best Picture at the 2027 Academy Awards?

MARKET PRICE:
YES = 0.42, NO = 0.58

TOP YES EVIDENCE:
1. Film has received critical acclaim at major festivals
   Sources: 5 | Agreement: high | Value: 0.87

...
```

---

## Troubleshooting

### Issue: "Module not found"
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: "Redis connection failed"
```bash
# Check Redis is running
docker ps | grep redis-vector

# Start if not running
docker start redis-vector

# Or start fresh
docker run -d --name redis-vector -p 6379:6379 redis/redis-stack:latest
```

### Issue: "Claude API error"
```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Set if missing
export ANTHROPIC_API_KEY=your_key_here

# Or run without Claude (uses heuristics)
# The system gracefully falls back
```

### Issue: "Kalshi authentication failed"
```bash
# Verify credentials
echo $KALSHI_EMAIL
echo $KALSHI_USE_DEMO

# Use demo mode for testing
export KALSHI_USE_DEMO=true
```

---

## Next Steps

1. **Test locally**: Run `python -m app.compression.demo_advanced_compression`
2. **Review output**: Check `examples/outputs/advanced_compression_result.json`
3. **Try Redis**: Run `--redis` flag to see vector search in action
4. **Deploy**: Upload standalone agents to Agentverse (see `AGENTVERSE_DEPLOYMENT_GUIDE.md`)

---

## Documentation

- **Full deployment guide**: See `AGENTVERSE_DEPLOYMENT_GUIDE.md`
- **Redis integration**: See `REDIS_INTEGRATION.md`
- **Compression details**: See `COMPRESSION_AGENT_SUMMARY.md`
- **Architecture overview**: See `README.md`

---

## Support

If you encounter issues:
1. Check this guide first
2. Review the inline documentation in agent files
3. Check Redis logs: `docker logs redis-vector`
4. Run tests: `pytest tests/test_advanced_compression.py -v`
