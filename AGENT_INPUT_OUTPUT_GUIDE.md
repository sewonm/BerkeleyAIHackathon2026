# Agent Input/Output Guide - Complete Pipeline

## Pipeline Flow

```
Sports/Financial Agent → Compression Agent → Decision Agent → Kalshi Agent
   (Evidence)          (Compressed Context)   (Decision)      (Execution)
```

---

## 1. Sports Video Agent → Compression Agent

### Sports Video Agent Output (EvidenceChunkMsg)

**Format:**
```json
{
  "source_type": "sports_video",
  "text": "<raw evidence text>",
  "source_url": "https://site.api.espn.com/...",
  "confidence": 0.9,
  "metadata": {
    "kind": "score_state | box_stats | event_log | odds | win_probability | injuries | lineups | deep_stats | match_thread | preview | news | article",
    "fetched_via": "http | browserbase | search",
    "source_strength": "anchor | noisy",
    "observed_at": "2026-06-20T00:00:00Z",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447"
  }
}
```

**Example - Score & State:**
```json
{
  "source_type": "sports_video",
  "text": "France 2-1 Brazil (Final). France wins the match with goals from Mbappe (23', 67') and Brazil's Neymar (45+2'). Match status: Final. Attendance: 88,966 at Lusail Stadium.",
  "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
  "confidence": 0.95,
  "metadata": {
    "kind": "score_state",
    "fetched_via": "http",
    "source_strength": "anchor",
    "observed_at": "2026-06-20T22:45:00Z",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447",
    "event_name": "France vs Brazil"
  }
}
```

**Example - Odds & Win Probability:**
```json
{
  "source_type": "sports_video",
  "text": "Betting odds: France -120 (45.5% implied), Brazil +150 (40.0% implied), Draw +200 (33.3% implied). Win probability model: France 52%, Brazil 31%, Draw 17%. Line movement: France opened at -110, moved to -120 (increased 9% in last 24h).",
  "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
  "confidence": 0.88,
  "metadata": {
    "kind": "odds",
    "fetched_via": "http",
    "source_strength": "anchor",
    "observed_at": "2026-06-20T18:00:00Z",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447"
  }
}
```

**Example - Injuries:**
```json
{
  "source_type": "sports_video",
  "text": "France: Kylian Mbappe (Healthy), Antoine Griezmann (Healthy), N'Golo Kante (Questionable - ankle). Brazil: Neymar (Probable - minor knock), Vinicius Jr (Healthy), Casemiro (Out - suspended).",
  "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
  "confidence": 0.92,
  "metadata": {
    "kind": "injuries",
    "fetched_via": "http",
    "source_strength": "anchor",
    "observed_at": "2026-06-20T16:30:00Z",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447"
  }
}
```

### Compression Agent Input (EnhancedEvidenceChunk)

**Expected fields:**
- `market_id` (string): Identifier for the market
- `source_agent` (string): Which agent collected this (e.g., "sports_video_agent")
- `source_type` (string): Type of evidence ("sports_video", "financial_research", etc.)
- `text` (string): **The actual evidence content**
- `source_url` (optional string): URL where evidence was found
- `timestamp` (optional string): When collected
- `confidence` (optional float): 0.0-1.0, defaults to 0.8
- `metadata` (optional dict): Additional data

**Manual test input for Compression Agent:**

```json
{
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "evidence_chunks": [
    {
      "market_id": "france-worldcup-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France 2-1 Brazil (Final). France wins with goals from Mbappe (23', 67') and Brazil's Neymar (45+2'). Attendance: 88,966 at Lusail Stadium.",
      "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
      "confidence": 0.95,
      "metadata": {
        "kind": "score_state",
        "sport": "soccer",
        "league": "fifa.world",
        "event_id": "760447"
      }
    },
    {
      "market_id": "france-worldcup-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "Betting odds: France -120 (45.5% implied), Brazil +150. Win probability: France 52%, Brazil 31%, Draw 17%. Line moved from -110 to -120 (+9% in 24h).",
      "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
      "confidence": 0.88,
      "metadata": {
        "kind": "odds",
        "sport": "soccer"
      }
    },
    {
      "market_id": "france-worldcup-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France: Mbappe (Healthy), Griezmann (Healthy), Kante (Questionable - ankle). Brazil: Neymar (Probable - minor knock), Casemiro (Out - suspended).",
      "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
      "confidence": 0.92,
      "metadata": {
        "kind": "injuries",
        "sport": "soccer"
      }
    }
  ],
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "aggressiveness": 0.5
}
```

---

## 2. Compression Agent → Decision Agent

### Compression Agent Output (AdvancedCompressionResult)

**Format:**
```python
{
  "request_id": "uuid",
  "market_id": "france-worldcup-2026",
  "status": "success",
  "compression_result": {
    "compressed_context": "<formatted text>",
    "metrics": {
      "raw_token_count": 450,
      "compressed_token_count": 180,
      "compression_ratio": 2.5,
      "total_claims_extracted": 8,
      "total_consensus_items": 5,
      "yes_consensus_count": 3,
      "no_consensus_count": 2
    },
    "top_supporting_evidence": [
      {
        "canonical_claim": "France won 2-1 against Brazil in recent match",
        "supporting_chunks": 2,
        "consensus_score": 0.95,
        "direction": "YES"
      }
    ],
    "top_opposing_evidence": [
      {
        "canonical_claim": "Key player Kante is questionable with ankle injury",
        "supporting_chunks": 1,
        "consensus_score": 0.75,
        "direction": "NO"
      }
    ],
    "contradictions": [],
    "missing_info": ["Opponent team not specified", "Tournament stage unclear"]
  }
}
```

**Example compressed_context output:**

```
MARKET: Will France win the World Cup 2026?

TOP YES EVIDENCE (3 items, 62% confidence):
• France defeated Brazil 2-1 in their most recent match with goals from Mbappe
• Betting markets favor France at 52% win probability vs Brazil's 31%
• Key French players Mbappe and Griezmann are healthy and in good form

TOP NO EVIDENCE (2 items, 38% confidence):
• N'Golo Kante is questionable with an ankle injury
• Brazil's Casemiro is suspended, but this may actually favor France

CONTRADICTIONS:
(None detected - evidence is consistent)

MISSING INFORMATION:
• Specific tournament stage not identified
• Opponent in World Cup final is unknown
• Current France FIFA ranking not provided

CONSENSUS: France shows strong recent form and favorable odds, but injury concerns for Kante create some uncertainty. Evidence suggests France is the favorite but not a certainty.
```

### Decision Agent Input

**Expected fields:**
- `market_question` (string): The question
- `current_yes_price` (float): Current YES price (0.0-1.0)
- `current_no_price` (float): Current NO price (0.0-1.0)
- `compressed_context` (string): **The compressed evidence text from compression agent**
- `resolution_criteria` (optional string): How market resolves
- `max_position_size` (optional float): Max $ to risk, defaults to 100.0
- `risk_tolerance` (optional string): "conservative" | "moderate" | "aggressive", defaults to "moderate"

**Manual test input for Decision Agent:**

```json
{
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "compressed_context": "MARKET: Will France win the World Cup 2026?\n\nTOP YES EVIDENCE (3 items, 62% confidence):\n• France defeated Brazil 2-1 in their most recent match with goals from Mbappe\n• Betting markets favor France at 52% win probability vs Brazil's 31%\n• Key French players Mbappe and Griezmann are healthy and in good form\n\nTOP NO EVIDENCE (2 items, 38% confidence):\n• N'Golo Kante is questionable with an ankle injury\n• Brazil's Casemiro is suspended, but this may actually favor France\n\nCONSENSUS: France shows strong recent form and favorable odds, but injury concerns for Kante create some uncertainty.",
  "max_position_size": 100.0,
  "risk_tolerance": "moderate"
}
```

---

## 3. Decision Agent → Kalshi Agent

### Decision Agent Output (TradingDecision)

**Format:**
```python
{
  "request_id": "uuid",
  "market_id": "france-worldcup-2026",
  "market_question": "Will France win the World Cup 2026?",
  "action": "BUY_YES",  # or "BUY_NO" or "HOLD"
  "side": "yes",  # or "no"
  "estimated_fair_value": 0.585,
  "current_market_price": 0.52,
  "edge": 0.065,  # 6.5% edge
  "confidence": 0.712,
  "kelly_fraction": 0.185,
  "suggested_position_size": 18.50,
  "max_position_size": 100.0,
  "reasoning": "Based on recent match performance and betting market analysis, France appears undervalued at current price of 52%. Fair value estimate of 58.5% suggests 6.5% edge. Injury concern for Kante adds uncertainty but overall evidence supports YES position.",
  "key_evidence": [
    "France won recent match against Brazil 2-1",
    "Betting markets show 52% win probability",
    "Key offensive players healthy and performing well"
  ],
  "risk_factors": [
    "N'Golo Kante questionable with ankle injury",
    "Limited information on tournament stage",
    "World Cup outcomes historically volatile"
  ],
  "missing_info": [
    "Opponent in final not specified",
    "Tournament stage unclear",
    "Recent head-to-head record not provided"
  ]
}
```

### Kalshi Agent Input (ExecuteTradeRequest)

**Expected fields:**
- `market_id` (string): Market identifier
- `market_title` (string): Human-readable title
- `action` (string): "BUY_YES" | "BUY_NO" | "SELL_YES" | "SELL_NO" | "HOLD"
- `side` (string): "yes" | "no"
- `quantity` (int): Number of contracts
- `fair_probability` (float): Decision agent's fair value estimate
- `confidence` (float): Confidence level (0.0-1.0)

**Manual test input for Kalshi Agent:**

```json
{
  "market_id": "france-worldcup-2026",
  "market_title": "Will France win the World Cup 2026?",
  "action": "BUY_YES",
  "side": "yes",
  "quantity": 18,
  "fair_probability": 0.585,
  "confidence": 0.712
}
```

---

## Quick Reference: Agent Inputs

### Test Compression Agent Directly

Type in ASI:One chat:
```
@compression-agent demo
```

Or send JSON:
```json
{
  "market_question": "Will France win?",
  "evidence_chunks": [
    {"market_id": "test", "source_agent": "sports", "source_type": "sports_video", "text": "France won 2-1"}
  ]
}
```

### Test Decision Agent Directly

Type in ASI:One chat:
```
@decision-agent demo
```

Or send JSON:
```json
{
  "market_question": "Will France win?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "compressed_context": "MARKET: Will France win?\n\nTOP YES EVIDENCE:\n• France won recent match 2-1\n\nCONSENSUS: France favored"
}
```

---

## Schema References

### EvidenceChunkMsg (from sports_video_agent)
```python
{
  "source_type": str,  # "sports_video"
  "text": str,  # Evidence content
  "source_url": str | None,
  "timestamp": str | None,
  "confidence": float | None,  # 0.0-1.0, default 0.8
  "metadata": dict  # Any additional data
}
```

### EnhancedEvidenceChunk (compression agent input)
```python
{
  "market_id": str,
  "source_agent": str,  # "sports_video_agent"
  "source_type": str,  # "sports_video"
  "text": str,  # Evidence content
  "source_url": str | None,
  "timestamp": str | None,
  "confidence": float | None,  # Default 0.8
  "metadata": dict
}
```

### Key Differences
- Sports agent uses `source_type` only
- Compression agent adds `market_id` and `source_agent`
- Both have `text`, `source_url`, `confidence`, `metadata`

---

## Error Fixed

**Original error:**
```
'AdvancedCompressionResult' object has no attribute 'top_yes_evidence'
```

**Fixed:**
Changed `result.top_yes_evidence` → `result.top_supporting_evidence`
Changed `result.top_no_evidence` → `result.top_opposing_evidence`

The compression agent demo should now work with `@compression-agent demo`!

---

**Last Updated:** 2026-06-20
