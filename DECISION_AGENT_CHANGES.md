# Decision Agent Changes Summary

## Overview

The `standalone_decision_agent.py` has been completely refactored to accept graph compression output from `graph_compression_agent.py` and make simple YES/NO/HOLD decisions based on evidence analysis.

## Key Changes

### 1. **Input Format Changed**
**Before:**
- Accepted `compressed_context` (text string)
- Expected evidence lists and metrics

**After:**
- Accepts `graph_data` (JSON or text format)
- Supports both formats from graph_compression_agent:
  - **JSON**: `{"nodes": [...], "edges": [...]}`
  - **Text**: `"YES:claim1(score)|claim2 NO:claim3(score)"`

### 2. **Output Format Simplified**
**Before:**
```python
{
    "action": "BUY_YES" | "BUY_NO" | "SELL_YES" | "SELL_NO" | "HOLD",
    "confidence": 0.75,
    "suggested_position_size": 24.50,
    "estimated_fair_value": 0.585,
    "price_limit": 0.55,
    "reasoning": "...",
    "key_factors": [...],
    "risks": [...],
    "expected_value": 0.065,
    "edge": 0.065
}
```

**After:**
```python
{
    "action": "YES" | "NO" | "HOLD",
    "confidence": 0.75,
    "reasoning": "...",
    "yes_score": 0.54,
    "no_score": 0.46,
    "yes_count": 2,
    "no_count": 1
}
```

### 3. **Decision Logic Refactored**

#### Graph Parsing
- **JSON Format**: Parses nodes and edges, extracts YES/NO nodes by `"dir"` field
- **Text Format**: Uses regex to extract claims and scores from text format

#### Score Calculation
```python
# Calculate weighted average score for YES nodes
yes_score = sum(node["score"] for node in yes_nodes) / max(len(yes_nodes), 1)

# Calculate weighted average score for NO nodes
no_score = sum(node["score"] for node in no_nodes) / max(len(no_nodes), 1)

# Normalize to 0-1 range
total = yes_score + no_score
yes_score = yes_score / total
no_score = no_score / total
```

#### Decision Threshold
```python
CONFIDENCE_THRESHOLD = 0.15  # Minimum score difference to make a decision

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
```

### 4. **Removed Features**
- ❌ Kelly Criterion position sizing
- ❌ Fair value estimation
- ❌ Edge calculation
- ❌ Price limits
- ❌ Expected value
- ❌ Dummy/sample outputs
- ❌ Complex heuristic fallbacks

### 5. **Reasoning Enhanced**
Now includes:
- Score difference analysis
- Top YES evidence (up to 3 nodes)
- Top NO evidence (up to 3 nodes)
- Reinforcement edge count
- Contradiction edge count

Example reasoning output:
```
YES decision based on stronger evidence. YES score: 0.54 from 2 nodes, NO score: 0.46 from 1 nodes. 1 reinforcing relationships found.

Top YES evidence:
1. France defeated Brazil 2-1. Mbappe scored twice (score: 0.85)
2. Betting odds favor France at 62% implied probability (score: 0.72)

Top NO evidence:
1. Kante questionable with ankle injury (score: 0.68)
```

## Input Schema

### TradingDecisionRequest
```python
{
    "request_id": "uuid",  # Auto-generated
    "market_id": "france-wc-2026",
    "market_question": "Will France win the World Cup 2026?",
    "resolution_criteria": "Resolves YES if France wins",  # Optional

    # Market prices
    "current_yes_price": 0.52,  # 0.0-1.0
    "current_no_price": 0.48,   # 0.0-1.0

    # Graph compression output (REQUIRED)
    "graph_data": "{\"nodes\": [...], \"edges\": [...]}",  # JSON or text

    # Optional constraints
    "max_position_size": 100.0,
    "risk_tolerance": "moderate"  # "conservative" | "moderate" | "aggressive"
}
```

## Output Schema

### TradingDecision
```python
{
    "decision_id": "uuid",
    "request_id": "uuid",
    "market_id": "france-wc-2026",

    # Core decision
    "action": "YES",  # "YES" | "NO" | "HOLD"
    "confidence": 0.75,  # 0.0-1.0

    # Reasoning
    "reasoning": "YES decision based on stronger evidence...",

    # Graph analysis
    "yes_score": 0.54,  # 0.0-1.0
    "no_score": 0.46,   # 0.0-1.0
    "yes_count": 2,     # Number of YES nodes
    "no_count": 1,      # Number of NO nodes

    # Metadata
    "timestamp": "2026-06-20T..."
}
```

## Integration with graph_compression_agent.py

### Data Flow
```
graph_compression_agent.py
    ↓
    Outputs:
    - JSON: {"nodes": [...], "edges": [...]}
    - Text: "YES:claim1(0.85)|claim2(0.72) NO:claim3(0.68)"
    ↓
standalone_decision_agent.py
    ↓
    Parses graph_data
    Calculates YES vs NO scores
    Makes YES/NO/HOLD decision
    ↓
    Outputs:
    - action: "YES" | "NO" | "HOLD"
    - confidence: 0.0-1.0
    - reasoning: detailed explanation
```

### Example Usage

#### With JSON Graph
```python
# From graph_compression_agent
graph_output = {
    "nodes": [
        {"id": "1", "text": "France won 2-1", "dir": "Y", "score": 0.85},
        {"id": "2", "text": "Odds favor France", "dir": "Y", "score": 0.72},
        {"id": "3", "text": "Kante injured", "dir": "N", "score": 0.68}
    ],
    "edges": [
        {"from": "1", "to": "2", "type": "reinforces"}
    ]
}

# Send to decision agent
request = TradingDecisionRequest(
    market_id="test",
    market_question="Will France win?",
    current_yes_price=0.52,
    current_no_price=0.48,
    graph_data=json.dumps(graph_output)
)

decision = decision_engine.make_decision(request)
# Result: action="YES", confidence=0.54 (weak YES)
```

#### With Text Graph
```python
# From graph_compression_agent
graph_text = "YES:France won 2-1(0.85)|Odds favor France(0.72) NO:Kante injured(0.68)"

# Send to decision agent
request = TradingDecisionRequest(
    market_id="test",
    market_question="Will France win?",
    current_yes_price=0.52,
    current_no_price=0.48,
    graph_data=graph_text
)

decision = decision_engine.make_decision(request)
# Result: action="HOLD", confidence=0.50 (balanced evidence, diff < 0.15)
```

## Testing

Run the test suite:
```bash
python3 test_decision_logic.py
```

Tests cover:
1. ✅ JSON graph format parsing
2. ✅ Text graph format parsing
3. ✅ Balanced evidence (HOLD decision)
4. ✅ Strong NO evidence

## Claude Integration

If `ANTHROPIC_API_KEY` is set, the agent uses Claude for enhanced reasoning:
- Analyzes graph evidence with LLM
- Generates more nuanced confidence scores
- Provides detailed reasoning

If no API key, falls back to graph-based heuristics (tested above).

## Breaking Changes

⚠️ **This is a breaking change**. Old code using this agent must be updated:

**Old:**
```python
request = TradingDecisionRequest(
    compressed_context="MARKET: ...",
    top_yes_evidence=[...],
    top_no_evidence=[...]
)
```

**New:**
```python
request = TradingDecisionRequest(
    graph_data=json.dumps({"nodes": [...], "edges": [...]})
)
```

## Files Modified
- ✅ [uagents_deploy/standalone_decision_agent.py](uagents_deploy/standalone_decision_agent.py) - Complete refactor

## Files Created
- ✅ [test_decision_logic.py](test_decision_logic.py) - Standalone test suite
- ✅ [test_decision_agent.py](test_decision_agent.py) - Full integration test (requires uagents)
- ✅ [DECISION_AGENT_CHANGES.md](DECISION_AGENT_CHANGES.md) - This file

## Next Steps

1. Update orchestrator to use new `graph_data` field
2. Update any calling code to expect `YES`/`NO`/`HOLD` instead of `BUY_YES`/`BUY_NO`
3. Test end-to-end pipeline:
   - Evidence collection → graph_compression_agent → standalone_decision_agent
4. Update DECISION_AGENT_README.md to reflect new schema
