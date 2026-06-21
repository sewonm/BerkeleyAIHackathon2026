# Fix: Raw Graph Input Support

## The Error You Encountered

```
ERROR: [decision_agent_standalone]: Chat handler error: 'market_question'
```

## Root Cause

You were sending **raw graph data** directly:
```json
{
  "nodes": [{...}],
  "edges": []
}
```

But the agent expected a **wrapped request** with all required fields:
```json
{
  "market_question": "...",      // ← Missing!
  "current_yes_price": 0.52,     // ← Missing!
  "current_no_price": 0.48,      // ← Missing!
  "graph_data": "{\"nodes\":[...],\"edges\":[]}"
}
```

## The Fix

Updated the chat handler to **detect and handle raw graph data** automatically:

```python
# Check if it's raw graph data (just nodes/edges or facts/market) without wrapper
if ("nodes" in request_data or "facts" in request_data) and "market_question" not in request_data:
    # User sent raw graph data without wrapper - use defaults
    decision_request = TradingDecisionRequest(
        market_id="chat-market",
        market_question="Market analysis request",
        resolution_criteria="",
        current_yes_price=0.50,  # Default to 50/50 market
        current_no_price=0.50,
        graph_data=json.dumps(request_data),  # Re-stringify the graph
        max_position_size=100.0,
        risk_tolerance="moderate",
    )
```

## Now You Can Send Either Format

### Option 1: Raw Graph Data (NEW - Now Supported!)

```json
{
  "nodes": [{
    "id": "82fd9333-3e6c-458c-949d-129f9829dbfe",
    "source": "unknown",
    "text": "Skip to main content Skip to navigation ESPN Search You have come to the ESPN Af",
    "dir": "Y",
    "score": 0.9,
    "merged": 0
  }],
  "edges": []
}
```

**What happens:**
- Agent detects `"nodes"` key without `"market_question"`
- Uses default values:
  - Market question: "Market analysis request"
  - Current prices: 0.50 YES, 0.50 NO
  - Risk tolerance: moderate
- Makes decision based on graph data

### Option 2: Full Wrapped Request (Original)

```json
{
  "market_question": "Will France win the World Cup 2026?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "{\"nodes\":[{...}],\"edges\":[]}"
}
```

**What happens:**
- Agent detects `"market_question"` key
- Uses your provided values
- Makes decision with full context

## Test It Now

Restart your agent:
```bash
python3 uagents_deploy/standalone_decision_agent.py
```

Then send your raw graph data:
```json
{
  "nodes": [{
    "id": "82fd9333-3e6c-458c-949d-129f9829dbfe",
    "source": "unknown",
    "text": "Skip to main content Skip to navigation ESPN Search You have come to the ESPN Af",
    "dir": "Y",
    "score": 0.9,
    "merged": 0
  }],
  "edges": []
}
```

### Expected Output

```
Trading Decision for: Market analysis request

Decision: YES
Confidence: 95.0%

Graph Analysis:
- YES Score: 1.00 (1 nodes)
- NO Score: 0.00 (0 nodes)

Reasoning:
YES decision based on stronger evidence. YES score: 1.00 from 1 nodes, NO score: 0.00 from 0 nodes.

Top YES evidence:
1. Skip to main content Skip to navigation ESPN Search You have come to the ESPN Af (confidence: 0.90)
```

## What Changed

### Before (Would Error)
```
User sends: {"nodes": [...], "edges": []}
Agent tries: request_data["market_question"]
Result: ❌ KeyError: 'market_question'
```

### After (Works!)
```
User sends: {"nodes": [...], "edges": []}
Agent detects: "nodes" key, no "market_question"
Agent uses: Default values
Result: ✅ Decision made with graph data
```

## Summary

✅ **You can now send raw graph data directly!**

No need to wrap it in a full request object. The agent will:
1. Detect it's raw graph data
2. Use sensible defaults
3. Make a decision based on the evidence

Just paste your graph_compression_agent.py output straight into the chat! 🎉
