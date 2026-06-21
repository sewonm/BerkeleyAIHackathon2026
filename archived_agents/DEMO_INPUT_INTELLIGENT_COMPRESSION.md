# Demo Input for standalone_decision_agent.py
## Using intelligent_compression_agent.py Output

Based on your test on ASI:One, here's the **corrected demo input** that will actually work:

## ✅ Working Demo Input (JSON Format)

Copy and paste this into ASI:One chat with `@decision-agent`:

```json
{
  "market_id": "france-wc-2026",
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "{\"market\": {\"question\": \"Will France win the World Cup 2026?\", \"protected_terms\": [\"France\", \"World Cup\", \"2026\", \"Mbappe\", \"Pogba\"]}, \"facts\": [{\"text\": \"France beat Brazil 2-1 in thrilling match\", \"confidence\": 0.95, \"source_type\": \"sports_video\", \"source_url\": \"https://espn.com/match\", \"relation_to_market\": \"supports\", \"relation_strength\": 0.95}, {\"text\": \"Mbappe scored twice showing excellent form\", \"confidence\": 0.90, \"source_type\": \"sports_video\", \"source_url\": \"https://espn.com/match\", \"relation_to_market\": \"supports\", \"relation_strength\": 0.90}, {\"text\": \"France won 4 of last 5 matches\", \"confidence\": 0.85, \"source_type\": \"sports_stats\", \"source_url\": null, \"relation_to_market\": \"supports\", \"relation_strength\": 0.85}, {\"text\": \"Pogba with ankle injury affecting midfield\", \"confidence\": 0.80, \"source_type\": \"injury_report\", \"source_url\": null, \"relation_to_market\": \"contradicts\", \"relation_strength\": 0.80}, {\"text\": \"Midfield depth concerns without key player\", \"confidence\": 0.75, \"source_type\": \"analysis\", \"source_url\": null, \"relation_to_market\": \"contradicts\", \"relation_strength\": 0.75}], \"summary\": {\"total_facts\": 5, \"supporting\": 3, \"contradicting\": 2, \"neutral\": 0}}"
}
```

### Expected Output

```
Trading Decision for: Will France win the World Cup 2026?

Decision: HOLD
Confidence: 50.0%

Graph Analysis:
- YES Score: 0.57 (3 nodes)
- NO Score: 0.43 (2 nodes)

Reasoning:
Insufficient evidence difference. YES score: 0.57, NO score: 0.43. Difference (0.14) is below threshold (0.15).

Top YES evidence:
1. France beat Brazil 2-1 in thrilling match (confidence: 0.95)
2. Mbappe scored twice showing excellent form (confidence: 0.90)
3. France won 4 of last 5 matches (confidence: 0.85)

Top NO evidence:
1. Pogba with ankle injury affecting midfield (confidence: 0.80)
2. Midfield depth concerns without key player (confidence: 0.75)
```

## ✅ Working Demo Input (Text Format)

Alternatively, use the text format from intelligent_compression_agent.py:

```json
{
  "market_id": "france-wc-2026",
  "market_question": "Will France win the World Cup 2026?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "graph_data": "Q: Will France win the World Cup 2026?\nYES: France beat Brazil 2-1 in thrilling match(0.95)|Mbappe scored twice showing excellent form(0.90)|France won 4 of last 5 matches(0.85)\nNO: Pogba with ankle injury affecting midfield(0.80)|Midfield depth concerns without key player(0.75)"
}
```

## How the Parser Works Now

### Intelligent Compression JSON Format
```json
{
  "market": {...},
  "facts": [
    {"relation_to_market": "supports", "confidence": 0.95, "relation_strength": 0.95},
    {"relation_to_market": "contradicts", "confidence": 0.80, "relation_strength": 0.80}
  ]
}
```

**Parser Logic:**
1. Finds facts with `"relation_to_market": "supports"` → YES evidence
2. Finds facts with `"relation_to_market": "contradicts"` → NO evidence
3. Calculates weighted score: `confidence × relation_strength`
4. Averages scores and normalizes to 0-1 range
5. Makes decision based on score difference

### Intelligent Compression Text Format
```
Q: Will France win the World Cup 2026?
YES: fact1(0.95)|fact2(0.90)
NO: fact3(0.80)|fact4(0.75)
```

**Parser Logic:**
1. Regex extracts YES section (everything between `YES:` and `NO:` or end)
2. Regex extracts NO section (everything after `NO:`)
3. Parses each fact with score: `fact_text(score)`
4. Calculates average confidence scores
5. Makes decision based on score difference

## Decision Thresholds

```python
CONFIDENCE_THRESHOLD = 0.15

score_diff = yes_score - no_score

if abs(score_diff) < 0.15:
    action = "HOLD"
elif score_diff > 0:
    action = "YES"
else:
    action = "NO"
```

### Example Scenarios

| YES Score | NO Score | Difference | Decision | Confidence |
|-----------|----------|------------|----------|------------|
| 0.57      | 0.43     | +0.14      | **HOLD** | 50%        |
| 0.65      | 0.35     | +0.30      | **YES**  | 80%        |
| 0.30      | 0.70     | -0.40      | **NO**   | 90%        |
| 0.50      | 0.50     | 0.00       | **HOLD** | 50%        |

## Test Results

From `test_intelligent_decision.py`:

```
📊 Analysis Results:
  Supporting Facts: 3
  Contradicting Facts: 2
  YES Score: 0.574
  NO Score: 0.426

✅ Decision: HOLD
  Confidence: 50.0%

📝 Supporting Evidence:
  1. France beat Brazil 2-1 in thrilling match
     Confidence: 0.95, Strength: 0.95, Weighted: 0.90
  2. Mbappe scored twice showing excellent form
     Confidence: 0.90, Strength: 0.90, Weighted: 0.81
  3. France won 4 of last 5 matches
     Confidence: 0.85, Strength: 0.85, Weighted: 0.72

📝 Contradicting Evidence:
  1. Pogba with ankle injury affecting midfield
     Confidence: 0.80, Strength: 0.80, Weighted: 0.64
  2. Midfield depth concerns without key player
     Confidence: 0.75, Strength: 0.75, Weighted: 0.56
```

## Why Your Previous Test Failed

**What you sent:**
```json
{
  "graph_data": "{\"market\": {...}, \"facts\": [...]}"
}
```

**What the old parser expected:**
```json
{
  "graph_data": "{\"nodes\": [...], \"edges\": [...]}"
}
```

**Result:** Parser couldn't find `"nodes"` key, so it returned:
- YES Score: 0.00 (0 nodes) ❌
- NO Score: 0.00 (0 nodes) ❌
- Decision: HOLD with 50% confidence (default fallback)

**Now the parser:**
1. ✅ Checks for `"facts"` and `"market"` keys (intelligent compression)
2. ✅ Parses `relation_to_market` field
3. ✅ Counts supporting vs contradicting facts
4. ✅ Returns correct YES/NO counts and scores

## Files Modified

- ✅ [uagents_deploy/standalone_decision_agent.py](uagents_deploy/standalone_decision_agent.py)
  - Added `_analyze_intelligent_compression()` method
  - Updated `_parse_graph_data()` to detect format
  - Updated `_analyze_text_format()` for intelligent compression text
  - Updated reasoning display to show fact confidence

## Files Created

- ✅ [test_intelligent_decision.py](test_intelligent_decision.py) - Comprehensive test suite
- ✅ [DEMO_INPUT_INTELLIGENT_COMPRESSION.md](DEMO_INPUT_INTELLIGENT_COMPRESSION.md) - This file

Run `python3 test_intelligent_decision.py` to verify the parser works correctly! 🎉
