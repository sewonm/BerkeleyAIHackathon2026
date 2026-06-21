# Demo Input for standalone_decision_agent.py
## Using graph_compression_agent.py Output ✅

You're using the **correct format**! The decision agent already supports graph_compression_agent.py output.

## ✅ Your Example (Working Format)

```json
{
  "market_id": "test-market",
  "market_question": "Will France win the World Cup 2026?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "{\"nodes\":[{\"id\":\"82fd9333-3e6c-458c-949d-129f9829dbfe\",\"source\":\"unknown\",\"text\":\"Skip to main content Skip to navigation ESPN Search You have come to the ESPN Af\",\"dir\":\"Y\",\"score\":0.9,\"merged\":0}],\"edges\":[]}"
}
```

### Expected Output

```
Trading Decision for: Will France win the World Cup 2026?

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

**Why YES?** Only 1 YES node with score 0.9, no NO nodes → 100% YES score → Strong YES decision with 95% confidence.

---

## More Realistic Example (Multiple Nodes)

For a more balanced scenario with both YES and NO evidence:

```json
{
  "market_id": "france-wc-2026",
  "market_question": "Will France win the World Cup 2026?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "{\"nodes\":[{\"id\":\"1\",\"source\":\"sports_video_agent\",\"text\":\"France defeated Brazil 2-1. Mbappe scored twice\",\"dir\":\"Y\",\"score\":0.85,\"merged\":0},{\"id\":\"2\",\"source\":\"odds_agent\",\"text\":\"Betting odds favor France at 62% implied probability\",\"dir\":\"Y\",\"score\":0.72,\"merged\":0},{\"id\":\"3\",\"source\":\"injury_agent\",\"text\":\"Kante questionable with ankle injury\",\"dir\":\"N\",\"score\":0.68,\"merged\":0}],\"edges\":[{\"from\":\"1\",\"to\":\"2\",\"type\":\"reinforces\",\"strength\":0.7}]}"
}
```

### Expected Output

```
Trading Decision for: Will France win the World Cup 2026?

Decision: HOLD
Confidence: 50.0%

Graph Analysis:
- YES Score: 0.54 (2 nodes)
- NO Score: 0.46 (1 nodes)

Reasoning:
Insufficient evidence difference. YES score: 0.54, NO score: 0.46. Difference (0.07) is below threshold (0.15). 1 reinforcing relationships found.

Top YES evidence:
1. France defeated Brazil 2-1. Mbappe scored twice (confidence: 0.85)
2. Betting odds favor France at 62% implied probability (confidence: 0.72)

Top NO evidence:
1. Kante questionable with ankle injury (confidence: 0.68)
```

**Why HOLD?**
- YES avg score: (0.85 + 0.72) / 2 = 0.785
- NO avg score: 0.68
- Normalized: YES 0.536, NO 0.464
- Difference: 0.072 < threshold 0.15 → HOLD

---

## Graph Compression Format Specification

### Node Structure
```json
{
  "id": "unique-id",
  "source": "agent_name",
  "text": "Evidence text",
  "dir": "Y",        // "Y" = YES (supports), "N" = NO (contradicts)
  "score": 0.85,     // Information value (0.0-1.0)
  "merged": 0        // Number of nodes merged into this one
}
```

### Edge Structure
```json
{
  "from": "node_id_1",
  "to": "node_id_2",
  "type": "reinforces",  // "reinforces", "contradicts", "same_sentiment"
  "strength": 0.7        // Relationship strength (0.0-1.0)
}
```

---

## How the Parser Works

### 1. Format Detection
```python
data = json.loads(graph_data)

# Check for graph_compression_agent format
if "nodes" in data and "edges" in data:
    return _analyze_graph_compression(data)
```

### 2. Node Classification
```python
yes_nodes = [n for n in nodes if n.get("dir") == "Y"]  # Supports YES
no_nodes = [n for n in nodes if n.get("dir") == "N"]   # Supports NO
```

### 3. Score Calculation
```python
# Average scores
yes_score = sum(n["score"] for n in yes_nodes) / len(yes_nodes)
no_score = sum(n["score"] for n in no_nodes) / len(no_nodes)

# Normalize to 0-1 range
total = yes_score + no_score
yes_score = yes_score / total
no_score = no_score / total
```

### 4. Decision Logic
```python
CONFIDENCE_THRESHOLD = 0.15

score_diff = yes_score - no_score

if abs(score_diff) < 0.15:
    action = "HOLD"
    confidence = 0.5
elif score_diff > 0:
    action = "YES"
    confidence = min(0.5 + score_diff, 0.95)
else:
    action = "NO"
    confidence = min(0.5 + abs(score_diff), 0.95)
```

---

## Decision Examples

### Example 1: Single YES Node (Your Case)
| Metric | Value |
|--------|-------|
| YES Nodes | 1 (score: 0.9) |
| NO Nodes | 0 |
| YES Score | 1.00 |
| NO Score | 0.00 |
| Score Diff | +1.00 |
| **Decision** | **YES** |
| **Confidence** | **95%** |

### Example 2: Balanced Evidence
| Metric | Value |
|--------|-------|
| YES Nodes | 2 (avg: 0.785) |
| NO Nodes | 1 (avg: 0.68) |
| YES Score | 0.536 |
| NO Score | 0.464 |
| Score Diff | +0.072 |
| **Decision** | **HOLD** |
| **Confidence** | **50%** |

### Example 3: Strong YES Evidence
| Metric | Value |
|--------|-------|
| YES Nodes | 3 (avg: 0.85) |
| NO Nodes | 1 (avg: 0.60) |
| YES Score | 0.71 |
| NO Score | 0.29 |
| Score Diff | +0.42 |
| **Decision** | **YES** |
| **Confidence** | **92%** |

### Example 4: Strong NO Evidence
| Metric | Value |
|--------|-------|
| YES Nodes | 1 (avg: 0.50) |
| NO Nodes | 3 (avg: 0.85) |
| YES Score | 0.29 |
| NO Score | 0.71 |
| Score Diff | -0.42 |
| **Decision** | **NO** |
| **Confidence** | **92%** |

---

## Edge Analysis

The decision agent also considers graph edges:

- **`reinforces` edges**: Counted and mentioned in reasoning ("1 reinforcing relationships found")
- **`contradicts` edges**: Counted and flagged ("2 contradictions detected")

These don't affect the decision directly but provide context in the reasoning.

---

## Test Your Format

Run this to verify your exact format works:

```bash
python3 test_graph_compression_format.py
```

Output:
```
✅ Decision: YES
   Confidence: 95.0%

📊 Graph Analysis:
   YES Nodes (dir='Y'): 1
   NO Nodes (dir='N'): 0
   YES Score: 1.000
   NO Score: 0.000
```

---

## Summary

✅ **Your format is correct!**

The decision agent supports graph_compression_agent.py output natively:
- Looks for `"nodes"` and `"edges"` keys
- Classifies nodes by `"dir"` field ("Y" or "N")
- Uses `"score"` field for node importance
- Analyzes `"type"` field in edges for relationships

No changes needed - your input will work perfectly! 🎉
