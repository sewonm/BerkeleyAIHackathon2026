# Agentverse Deployment Guide

This guide explains how to deploy the prediction market trading system to Fetch.ai Agentverse.

## System Architecture

The system consists of **4 standalone agents** that can be deployed independently to Agentverse:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                       │
│                   (User-Facing Agent)                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────┐
                            │                 │
                            ▼                 ▼
                    ┌───────────────┐  ┌───────────────┐
                    │  COMPRESSION  │  │   DECISION    │
                    │     AGENT     │─▶│     AGENT     │
                    └───────────────┘  └───────────────┘
                            │                 │
                            │                 ▼
                            │          ┌───────────────┐
                            │          │    KALSHI     │
                            │          │ EXECUTION AGT │
                            │          └───────────────┘
                            ▼
                    ┌───────────────┐
                    │     REDIS     │
                    │ (Vector Store)│
                    └───────────────┘
```

## Standalone Agents for Agentverse

### 1. Compression Agent
**File**: `uagents_deploy/standalone_compression_agent.py`

**What it does**:
- Receives evidence chunks from research/orchestrator agent
- Extracts claims using Claude or heuristics
- Builds evidence graph
- Performs consensus clustering
- Scores by information value
- Returns compressed context

**Key Features**:
- ✅ **Self-contained**: No external `app/*` imports
- ✅ **Claude integration** with graceful fallback
- ✅ **Aggressiveness parameter** for compression control
- ✅ **Graph-consensus** compression algorithm
- ✅ **Information-theoretic** scoring

**Configuration**:
```bash
# Optional: For Claude-based claim extraction
ANTHROPIC_API_KEY=your_key_here
```

**Usage**:
```python
from uagents import Agent

# Send compression request
request = EnhancedCompressionRequest(
    market_id="MARKET-123",
    market_question="Will France win the World Cup?",
    resolution_criteria="...",
    current_yes_price=0.65,
    current_no_price=0.35,
    evidence_chunks=[...],
    aggressiveness=0.7  # 0=keep all, 1=only top items
)

# Agent will respond with:
# - Compressed context (text)
# - Top YES/NO evidence
# - Contradictions
# - Compression metrics
```

---

### 2. Decision Agent
**File**: `uagents_deploy/standalone_decision_agent.py`

**What it does**:
- Receives compressed context from Compression Agent
- Analyzes evidence
- Estimates fair market value
- Makes trading decision (BUY_YES/BUY_NO/HOLD)
- Calculates position sizing using Kelly Criterion

**Key Features**:
- ✅ **Self-contained**: No external `app/*` imports
- ✅ **Claude-based reasoning** with heuristic fallback
- ✅ **Kelly Criterion** position sizing
- ✅ **Risk tolerance** settings (conservative/moderate/aggressive)
- ✅ **Expected value** calculations

**Configuration**:
```bash
# Optional: For Claude-based decision reasoning
ANTHROPIC_API_KEY=your_key_here
```

**Usage**:
```python
# Send decision request
request = TradingDecisionRequest(
    market_id="MARKET-123",
    market_question="Will France win the World Cup?",
    resolution_criteria="...",
    current_yes_price=0.65,
    current_no_price=0.35,
    compressed_context="<compressed evidence>",
    max_position_size=100.0,
    risk_tolerance="moderate"
)

# Agent will respond with:
# - Action: BUY_YES, BUY_NO, or HOLD
# - Confidence: 0-1
# - Suggested position size: $X
# - Estimated fair value
# - Edge vs current price
# - Reasoning + key factors + risks
```

---

### 3. Kalshi Execution Agent
**File**: `uagents_deploy/standalone_kalshi_agent.py`

**What it does**:
- Receives trading decisions from Decision Agent
- Connects to Kalshi API
- Places orders (market or limit)
- Monitors order status
- Reports execution results

**Key Features**:
- ✅ **Self-contained**: No external `app/*` imports
- ✅ **Kalshi API integration** (demo + production)
- ✅ **Smart execution** strategies
- ✅ **Risk management** (max slippage, timeouts)
- ✅ **Order monitoring** and status updates

**Configuration**:
```bash
# Required: Kalshi API credentials
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password

# Optional: Use demo mode (default: true)
KALSHI_USE_DEMO=true  # or false for production
```

**Usage**:
```python
# Send order request
request = KalshiOrderRequest(
    decision_id="DECISION-123",
    market_id="KXPRESI-2024",  # Kalshi ticker
    action="BUY_YES",
    quantity=10,  # Number of contracts
    order_type="limit",
    limit_price=67,  # Price in cents (0-100)
    max_slippage=0.02
)

# Agent will respond with:
# - Order ID
# - Status: pending/submitted/filled/error
# - Fill details (quantity, price, cost)
# - Error messages (if any)
```

---

### 4. Redis Vector Search (Optional)
**File**: `app/compression/redis_similarity.py`

**What it does**:
- Stores evidence chunks and claims as vectors
- Performs semantic similarity search
- Measures source diversity
- Caches compression results

**Key Features**:
- ✅ **Sentence-BERT embeddings** (all-MiniLM-L6-v2)
- ✅ **Fallback to simple embeddings** if sentence-transformers not available
- ✅ **Source deduplication** via cosine similarity
- ✅ **Enhanced claim clustering** beyond token overlap
- ✅ **Compression caching** for performance

**Configuration**:
```bash
# Optional: Redis connection URL
REDIS_URL=redis://localhost:6379
```

**Usage in Compression Agent**:
```python
from app.compression.redis_similarity import RedisVectorSearch

# Initialize
redis_search = RedisVectorSearch(
    redis_url="redis://localhost:6379",
    embedding_model="sentence-transformer"
)

# Find similar chunks (deduplicate sources)
similar = redis_search.find_similar_chunks(
    text="France won the semi-final...",
    market_id="MARKET-123",
    top_k=5,
    similarity_threshold=0.85
)

# Measure source diversity
diversity = redis_search.measure_source_diversity(
    chunks=evidence_chunks,
    similarity_threshold=0.85
)
# Returns: {
#   "total_sources": 10,
#   "effective_unique_sources": 7,
#   "diversity_score": 0.7,
#   "duplicate_groups": [...]
# }
```

---

## Deployment Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Core dependencies**:
- `uagents>=0.12.0` - Fetch.ai uAgents framework
- `anthropic>=0.18.0` - Claude API (optional)
- `redis>=5.0.0` - Redis client (optional)
- `sentence-transformers>=2.2.0` - Semantic embeddings (optional)
- `requests>=2.31.0` - HTTP client for Kalshi API

### Step 2: Set Environment Variables

Create a `.env` file:

```bash
# Claude API (optional but recommended)
ANTHROPIC_API_KEY=your_claude_api_key

# Kalshi API (required for execution agent)
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Set to false for production

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

### Step 3: Test Locally

Test each agent individually:

```bash
# Test Compression Agent
python uagents_deploy/standalone_compression_agent.py

# Test Decision Agent
python uagents_deploy/standalone_decision_agent.py

# Test Kalshi Execution Agent
python uagents_deploy/standalone_kalshi_agent.py
```

### Step 4: Deploy to Agentverse

**Option A: Using Agentverse Web UI**

1. Go to [Agentverse](https://agentverse.ai/)
2. Create new agent
3. Copy the contents of the standalone file
4. Set environment variables in Agentverse
5. Deploy

**Option B: Using Agentverse CLI**

```bash
# Install Agentverse CLI
pip install agentverse-cli

# Deploy Compression Agent
agentverse deploy uagents_deploy/standalone_compression_agent.py \
  --name compression-agent \
  --env ANTHROPIC_API_KEY=your_key

# Deploy Decision Agent
agentverse deploy uagents_deploy/standalone_decision_agent.py \
  --name decision-agent \
  --env ANTHROPIC_API_KEY=your_key

# Deploy Kalshi Execution Agent
agentverse deploy uagents_deploy/standalone_kalshi_agent.py \
  --name kalshi-agent \
  --env KALSHI_EMAIL=your_email \
  --env KALSHI_PASSWORD=your_password \
  --env KALSHI_USE_DEMO=true
```

### Step 5: Connect Agents

After deployment, get the agent addresses from Agentverse:

```python
COMPRESSION_AGENT_ADDRESS = "agent1qw..."
DECISION_AGENT_ADDRESS = "agent1qx..."
KALSHI_AGENT_ADDRESS = "agent1qy..."
```

Update your orchestrator or client to send messages to these addresses.

---

## Message Flows

### Flow 1: Full Trading Pipeline

```
User → Orchestrator → [Research Agents] → Compression Agent → Decision Agent → Kalshi Agent → Kalshi API
```

**Step-by-step**:

1. **User sends request** to Orchestrator
   ```python
   {
       "market_question": "Will France win the World Cup?",
       "max_position_size": 100.0,
       "risk_tolerance": "moderate"
   }
   ```

2. **Orchestrator** gathers evidence (calls research agents or fetches data)

3. **Compression Agent** compresses evidence
   ```python
   EnhancedCompressionRequest(
       market_id="...",
       market_question="...",
       evidence_chunks=[...],
       aggressiveness=0.7
   )
   # → EnhancedCompressionResponse(compressed_context=...)
   ```

4. **Decision Agent** makes decision
   ```python
   TradingDecisionRequest(
       market_id="...",
       compressed_context="...",
       current_yes_price=0.65,
       max_position_size=100.0
   )
   # → TradingDecisionResponse(decision=...)
   ```

5. **Kalshi Agent** executes trade
   ```python
   KalshiOrderRequest(
       market_id="KXPRESI-2024",
       action="BUY_YES",
       quantity=10,
       limit_price=67
   )
   # → KalshiOrderResponse(order_status=...)
   ```

---

## Advanced Features

### 1. Aggressiveness Control

Control how aggressively the Compression Agent filters evidence:

```python
request = EnhancedCompressionRequest(
    ...,
    aggressiveness=0.9  # 0.0 = keep all, 1.0 = only top items
)
```

**How it works**:
- Filters consensus items by `information_value >= (aggressiveness * 0.6)`
- `aggressiveness=0.0`: Keep all items (min compression)
- `aggressiveness=0.5`: Keep items with value ≥ 0.3 (moderate)
- `aggressiveness=1.0`: Keep items with value ≥ 0.6 (aggressive)

### 2. Risk Tolerance

Control position sizing in Decision Agent:

```python
request = TradingDecisionRequest(
    ...,
    risk_tolerance="conservative"  # or "moderate" or "aggressive"
)
```

**Position sizing multipliers**:
- `conservative`: 0.25x Kelly fraction
- `moderate`: 0.5x Kelly fraction
- `aggressive`: 1.0x Kelly fraction

### 3. Redis Vector Search

Enable semantic similarity for better compression:

```python
from app.compression.redis_similarity import RedisVectorSearch

redis_search = RedisVectorSearch(
    redis_url="redis://localhost:6379",
    embedding_model="sentence-transformer"
)

# Use in compression pipeline
similar_chunks = redis_search.find_similar_chunks(...)
diversity_metrics = redis_search.measure_source_diversity(...)
```

---

## Troubleshooting

### Issue: "Module not found" errors on Agentverse

**Solution**: Use standalone agents that have no external imports:
- ✅ `standalone_compression_agent.py`
- ✅ `standalone_decision_agent.py`
- ✅ `standalone_kalshi_agent.py`

These files are **fully self-contained** with all schemas and logic inline.

### Issue: Claude API errors

**Solution**:
1. Check `ANTHROPIC_API_KEY` is set correctly
2. Agents will gracefully fall back to heuristic methods if Claude fails
3. Check Claude API credits/quota

### Issue: Kalshi API authentication fails

**Solution**:
1. Verify `KALSHI_EMAIL` and `KALSHI_PASSWORD` are correct
2. Use `KALSHI_USE_DEMO=true` for testing
3. Check if using correct API endpoint (demo vs production)

### Issue: Redis connection fails

**Solution**:
1. Redis is **optional** - agents work without it
2. Check `REDIS_URL` is correct
3. Ensure Redis server is running
4. Compression will use token-based similarity if Redis unavailable

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | No | - | Claude API key for LLM reasoning |
| `KALSHI_EMAIL` | Yes* | - | Kalshi account email |
| `KALSHI_PASSWORD` | Yes* | - | Kalshi account password |
| `KALSHI_USE_DEMO` | No | `true` | Use demo API (`true`) or production (`false`) |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL |

\* Required only for Kalshi Execution Agent

---

## API Reference

See the inline schemas in each standalone agent file:
- **Compression Agent**: `EnhancedCompressionRequest`, `EnhancedCompressionResponse`
- **Decision Agent**: `TradingDecisionRequest`, `TradingDecisionResponse`
- **Kalshi Agent**: `KalshiOrderRequest`, `KalshiOrderResponse`

---

## Performance Notes

### Compression Agent
- **With Claude**: ~2-5s per request (depends on evidence size)
- **Heuristic only**: ~0.5-1s per request
- **With Redis**: Additional ~0.1-0.3s for vector search

### Decision Agent
- **With Claude**: ~3-8s per request (complex reasoning)
- **Heuristic only**: ~0.1s per request

### Kalshi Agent
- **Order placement**: ~0.5-1s per order
- **Order status check**: ~0.2-0.5s per check

---

## Next Steps

1. **Deploy all 3 agents** to Agentverse
2. **Create an orchestrator** to coordinate them
3. **Add monitoring** for order execution
4. **Implement portfolio management** across multiple markets
5. **Add backtesting** for strategy validation

---

## Support

For issues or questions:
1. Check the inline documentation in each agent file
2. Review the schemas in `app/schemas/trading.py`
3. See compression details in `COMPRESSION_AGENT_SUMMARY.md`
4. Check Fetch.ai docs: https://docs.fetch.ai/
