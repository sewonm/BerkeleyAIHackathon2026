# Compression Agent Output Format - FIXED ✅

## Problem

The `intelligent_compression_agent` was outputting **text format** instead of **JSON graph format**:

**Wrong (text format):**
```
Q: Will France win the World Cup 2026? YES:Kylian Mbappé continues to shine, scoring twice in(0.65)
```

**Correct (JSON graph format):**
```json
{
  "nodes": [
    {"id": "market", "type": "market", "text": "Will France win the World Cup 2026?"},
    {"id": "fact_0", "type": "fact", "source": "sports_video", "text": "Kylian Mbappé...", "direction": "YES"}
  ],
  "edges": [
    {"from": "fact_0", "to": "market", "type": "supports", "strength": 0.7}
  ]
}
```

## Root Cause

The `CompressedGraph.to_json()` method was outputting a flat facts list, not a proper **graph structure with nodes and edges**.

## Fix Applied

### 1. Updated `intelligent_compressor.py` - New Graph JSON Output

Changed the `to_json()` method to output proper graph structure:

```python
def to_json(self) -> str:
    """Convert to JSON graph format with nodes and edges"""
    nodes = []
    edges = []

    # Create market node (central node)
    nodes.append({
        "id": "market",
        "type": "market",
        "text": self.market.question,
        "protected_terms": self.market.protected_terms
    })

    # Create fact nodes
    for i, fact in enumerate(self.facts):
        node_id = f"fact_{i}"

        # Determine direction
        if fact.relation_to_market == "supports":
            direction = "YES"
        elif fact.relation_to_market == "contradicts":
            direction = "NO"
        else:
            direction = "NEUTRAL"

        nodes.append({
            "id": node_id,
            "type": "fact",
            "source": fact.source_type,
            "text": fact.text,
            "confidence": round(fact.confidence, 2),
            "direction": direction
        })

        # Create edge from fact to market
        edges.append({
            "from": node_id,
            "to": "market",
            "type": fact.relation_to_market,
            "strength": round(fact.relation_strength, 2)
        })

    # Create fact-to-fact edges (contradicts between YES and NO facts)
    for i, fact1 in enumerate(self.facts):
        for j, fact2 in enumerate(self.facts):
            if i >= j:
                continue

            # If one supports and other contradicts, they contradict each other
            if (fact1.relation_to_market == "supports" and fact2.relation_to_market == "contradicts") or \
               (fact1.relation_to_market == "contradicts" and fact2.relation_to_market == "supports"):
                edges.append({
                    "from": f"fact_{i}",
                    "to": f"fact_{j}",
                    "type": "contradicts",
                    "strength": 0.8
                })

    graph = {
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "total_facts": len(self.facts),
            "supporting": len(self.supporting_facts),
            "contradicting": len(self.contradicting_facts),
            "neutral": len(self.neutral_facts)
        }
    }
    return json.dumps(graph, separators=(',', ':'))
```

### 2. Changed Default Output Format to JSON

In `intelligent_compression_agent.py`:

```python
# Before:
output_format = request_data.get("output_format", "text")

# After:
output_format = request_data.get("output_format", "json")
```

### 3. Updated Test Files

- [test_espn_input.json](test_espn_input.json): Changed `"output_format": "json"`
- [TEST_ESPN_ASI_ONE.md](TEST_ESPN_ASI_ONE.md): Updated expected output to show graph JSON
- [test_espn_compression.py](test_espn_compression.py): Pretty-prints JSON output

## Test Results

Running `python3 test_espn_compression.py` now outputs:

```json
{
  "nodes": [
    {
      "id": "market",
      "type": "market",
      "text": "Will France win the World Cup 2026?",
      "protected_terms": ["France", "World Cup", "2026", "Mbappe", "Kylian Mbappé", "Les Bleus"]
    },
    {
      "id": "fact_5",
      "type": "fact",
      "source": "sports_video",
      "text": "Kylian Mbappé continues to shine, scoring twice in the recent 2-1 victory over Brazil",
      "confidence": 0.65,
      "direction": "YES"
    }
    // ... 14 more fact nodes
  ],
  "edges": [
    {
      "from": "fact_5",
      "to": "market",
      "type": "supports",
      "strength": 0.7
    }
    // ... 14 more edges
  ],
  "metrics": {
    "total_facts": 15,
    "supporting": 1,
    "contradicting": 0,
    "neutral": 14
  }
}
```

**Metrics:**
- ✅ **2.86x compression** (676 tokens → 236 tokens)
- ✅ **15 facts extracted** from noisy ESPN HTML
- ✅ **Graph structure** with market as central node
- ✅ **Proper edges** showing fact-to-market relationships

## Graph Structure Explained

### Nodes

1. **Market node** (central node):
   - Contains the market question
   - Protected terms for relevance filtering
   - Type: "market"

2. **Fact nodes** (extracted facts):
   - Parsed from noisy text (ESPN HTML)
   - Source type (sports_video, financial_research, etc.)
   - Confidence score (0.0-1.0)
   - Direction: YES (supports), NO (contradicts), NEUTRAL

### Edges

1. **Fact-to-market edges**:
   - Type: supports, contradicts, neutral
   - Strength: 0.0-1.0 (relationship strength)
   - Shows how each fact relates to the market question

2. **Fact-to-fact edges** (future enhancement):
   - Type: contradicts (YES facts vs NO facts)
   - Strength: 0.8
   - Shows conflicts between facts

## Usage on ASI:One

Send this JSON to `intelligent_compression_agent`:

```json
{
  "market_question": "Will France win the World Cup 2026?",
  "protected_terms": ["France", "World Cup", "2026", "Mbappe"],
  "evidence_chunks": [
    {
      "source_type": "sports_video",
      "text": "<long noisy ESPN HTML>",
      "source_url": "https://espn.com/...",
      "confidence": 0.85,
      "metadata": {
        "kind": "article",
        "fetched_via": "browserbase",
        "source_strength": "noisy"
      }
    }
  ],
  "token_budget": 150,
  "output_format": "json"
}
```

The agent will respond with the graph JSON structure showing:
- Market question as central node
- Facts extracted from noisy text
- Relationship edges (supports/contradicts/neutral)
- Compression metrics

## Files Modified

1. [uagents_deploy/intelligent_compressor.py](uagents_deploy/intelligent_compressor.py:90-158) - New `to_json()` method
2. [uagents_deploy/intelligent_compression_agent.py](uagents_deploy/intelligent_compression_agent.py:106) - Default to JSON output
3. [test_espn_input.json](test_espn_input.json:22) - Use JSON output
4. [TEST_ESPN_ASI_ONE.md](TEST_ESPN_ASI_ONE.md:40-99) - Updated expected output
5. [test_espn_compression.py](test_espn_compression.py:51-65) - Pretty-print JSON

## Status

✅ **FIXED** - The intelligent_compression_agent now outputs proper JSON graph format with nodes and edges.

The agent is ready to use on ASI:One with the correct graph-based output format!
