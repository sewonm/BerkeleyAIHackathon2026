# Orchestrator Agent - Chat Interface Examples

## Sports Video Agent Integration ✅

The sports_video_agent is now integrated into the orchestrator!

**Agent Address**: `agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g`

---

## How to Test via Agentverse Chat

### Step 1: Configure Environment

```bash
# Set all agent addresses
export FINANCIAL_RESEARCH_AGENT_ADDRESS="agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7"
export SPORTS_VIDEO_AGENT_ADDRESS="agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g"
export COMPRESSION_AGENT_ADDRESS="<your_compression_agent_address>"
export DECISION_AGENT_ADDRESS="<your_decision_agent_address>"
```

### Step 2: Restart Orchestrator

```bash
# Kill old orchestrator
lsof -ti:8000 | xargs kill -9

# Start with new config
cd uagents_deploy
python orchestrator_agent.py
```

**Check logs for:**
```
ASI:One chat protocol: ENABLED (DeltaV compatible)
```

---

## Example Chat Prompts

The orchestrator expects **JSON format** with market details. Here are examples for different categories:

### Example 1: Sports Market (uses sports_video_agent)

```json
{
  "market_id": "nba-lakers-celtics-2026",
  "market_title": "Will Lakers beat Celtics?",
  "market_question": "Will the Los Angeles Lakers beat the Boston Celtics in their next matchup?",
  "category": "sports",
  "current_yes_price": 0.45,
  "current_no_price": 0.55,
  "resolution_criteria": "Resolves YES if Lakers win the game, NO if Celtics win or tie",
  "protected_terms": ["Lakers", "Celtics", "NBA"]
}
```

**What happens:**
1. Orchestrator receives your message
2. Sends `EvidenceRequest` to sports_video_agent
3. Sports agent fetches ESPN stats, odds, injuries, lineup data
4. Returns evidence to orchestrator
5. Compression agent compresses the evidence
6. Decision agent makes trading recommendation
7. You get final result with YES/NO/HOLD recommendation

---

### Example 2: Financial Market (uses financial_research_agent)

```json
{
  "market_id": "btc-100k-2026",
  "market_title": "Will Bitcoin reach $100k?",
  "market_question": "Will Bitcoin (BTC) reach $100,000 USD before end of 2026?",
  "category": "financial",
  "current_yes_price": 0.65,
  "current_no_price": 0.35,
  "resolution_criteria": "Resolves YES if Bitcoin reaches $100k USD on any major exchange before Dec 31, 2026",
  "protected_terms": ["Bitcoin", "BTC", "$100k"]
}
```

**What happens:**
1. Orchestrator sends to financial_research_agent
2. Financial agent fetches Kalshi market data (prices, volume, orderbook)
3. Evidence compressed and analyzed
4. Final trading recommendation returned

---

### Example 3: Multi-Agent Sports + Finance

```json
{
  "market_id": "superbowl-2027-spread",
  "market_title": "Chiefs to cover spread?",
  "market_question": "Will the Kansas City Chiefs cover the spread in Super Bowl 2027?",
  "category": "sports",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "resolution_criteria": "Resolves YES if Chiefs cover the betting spread",
  "protected_terms": ["Chiefs", "Super Bowl", "spread"]
}
```

**What happens:**
1. Orchestrator sends to BOTH sports_video_agent AND financial_research_agent
2. Sports agent: Live game stats, odds, injuries
3. Financial agent: Betting market data from Kalshi
4. Both evidence sets combined and compressed
5. Decision based on all available evidence

---

## Required Fields

All chat messages must include these fields:

### Required:
- **`market_id`** - Unique identifier (any string)
- **`market_title`** - Short title (1-2 sentences)
- **`market_question`** - Full question (detailed)
- **`category`** - One of: "sports", "financial", "culture", "politics"
- **`resolution_criteria`** - How the market resolves

### Optional but Recommended:
- **`current_yes_price`** - Current YES price (0.0-1.0)
- **`current_no_price`** - Current NO price (0.0-1.0)
- **`protected_terms`** - Important terms to preserve during compression

---

## Category Routing

The orchestrator uses the `category` field to route appropriately:

| Category | Evidence Agents Called |
|----------|------------------------|
| `"sports"` | sports_video_agent + financial_research_agent (if configured) |
| `"financial"` | financial_research_agent + sports_video_agent (if configured) |
| `"culture"` | culture_web_agent (if configured) + others |
| `"politics"` | culture_web_agent (if configured) + others |

**Note:** The orchestrator sends to ALL configured evidence agents regardless of category. The category is passed to each agent, which can use it to customize their evidence collection.

---

## Natural Language Support

If you send non-JSON text, you'll get a help message:

**You type:**
```
help
```

**Orchestrator responds:**
```
**Orchestrator Agent - Market Analysis Pipeline**

I coordinate the full multi-agent market analysis pipeline.

**How to use me**:
[Shows JSON format examples and required fields]
```

---

## Expected Response Flow

### 1. Immediate Acknowledgement
```
✓ Message received
```

### 2. Processing Notification (2-3 seconds)
```
**Market Analysis Started**

Market: Will Lakers beat Celtics?
Category: sports

Your analysis is being processed through the multi-agent pipeline:
1. Evidence collection from specialized agents
2. Compression of evidence context
3. Trading decision analysis
4. Final results

Results will be sent when analysis completes (typically 10-30 seconds).
```

### 3. Agent Status Update
```json
{
  "agent_name": "orchestrator_agent",
  "status": "processing",
  "message": "Starting analysis pipeline for: Will Lakers beat Celtics?"
}
```

### 4. Final Analysis Result (10-30 seconds)

**If all agents configured:**
```json
{
  "market_title": "Market Analysis",
  "recommendation": "YES",
  "confidence": 0.72,
  "fair_probability": 0.68,
  "reasoning": "Based on live sports data from ESPN showing Lakers strong recent form...",
  "key_evidence": [
    "Lakers won last 3 games against Celtics",
    "Current betting odds favor Lakers at 55%",
    "Key Celtics player listed as questionable"
  ],
  "missing_info": ["Historical head-to-head spread performance"],
  "agents_used": ["sports_video_agent", "financial_research_agent"],
  "processing_time_seconds": 15.3,
  "raw_token_count": 2450,
  "compressed_token_count": 890,
  "compression_ratio": 2.75
}
```

**If compression/decision agents missing:**
- Pipeline will stall after evidence collection
- No final result returned
- Check orchestrator logs for warnings

### 5. Completion Status
```json
{
  "agent_name": "orchestrator_agent",
  "status": "completed",
  "message": "Analysis complete: YES (72% confidence)"
}
```

---

## Testing Checklist

- [ ] Orchestrator running with updated code
- [ ] SPORTS_VIDEO_AGENT_ADDRESS configured
- [ ] FINANCIAL_RESEARCH_AGENT_ADDRESS configured
- [ ] Logs show "ASI:One chat protocol: ENABLED"
- [ ] Send sports market JSON via chat
- [ ] Receive "processing" notification
- [ ] Configure compression/decision agents for full pipeline
- [ ] Receive final analysis result

---

## Quick Copy-Paste Test

**Sports Example:**
```json
{"market_id":"test-sports-001","market_title":"Will Argentina beat Brazil?","market_question":"Will Argentina beat Brazil in their next FIFA World Cup qualifier match?","category":"sports","current_yes_price":0.58,"current_no_price":0.42,"resolution_criteria":"Resolves YES if Argentina wins","protected_terms":["Argentina","Brazil","World Cup"]}
```

**Financial Example:**
```json
{"market_id":"test-finance-001","market_title":"S&P 500 above 5000?","market_question":"Will S&P 500 close above 5000 by end of 2026?","category":"financial","current_yes_price":0.71,"current_no_price":0.29,"resolution_criteria":"Resolves YES if S&P 500 closes above 5000","protected_terms":["S&P 500"]}
```

---

## Current Agent Configuration

### ✅ Integrated:
- **sports_video_agent** - Live sports stats from ESPN + odds
- **financial_research_agent** - Kalshi market data

### ❌ Need Deployment:
- **compression_agent** - Context compression (required for pipeline)
- **decision_agent** - Trading decisions (required for pipeline)
- **culture_web_agent** - Culture/web evidence (optional)

---

## Summary

**Sports Agent Added:** ✅ `agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g`

**Orchestrator accepts JSON via chat with:**
- Market details (id, title, question)
- Category (sports, financial, culture, politics)
- Current prices (optional)
- Resolution criteria

**Response includes:**
- Trading recommendation (YES/NO/HOLD)
- Confidence level
- Evidence from all agents
- Compression metrics
- Processing time

**To get full pipeline working, deploy compression + decision agents!**
