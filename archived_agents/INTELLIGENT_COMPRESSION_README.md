# Intelligent Compression Agent 🧠🗜️

![Innovation Lab](https://img.shields.io/badge/innovationlab-blue)
![Hackathon](https://img.shields.io/badge/hackathon-green)

**Agent Address:** `agent1q...` (derived from seed)

Parses rough noisy text from research agents and builds market-centric compressed graphs with **3-10x compression**.

## What It Does

### Real NLP Parsing
- **JSON parsing** - Extracts facts from ESPN API responses, Kalshi market data
- **HTML parsing** - Extracts facts from Browserbase scrapes
- **Text parsing** - Extracts facts from plain text chunks

### Market-Centric Graph
```
         [Market: Will France win WC 2026?]
                ↑           ↑           ↑
          supports    supports    contradicts
               ↑           ↑           ↑
          [France     [Odds       [Pogba
          beat        favor       injured]
          Brazil]     France]
```

### Intelligent Compression
1. Parse noisy JSON/HTML/text → Extract clean facts
2. Deduplicate similar facts
3. Classify relationship to market (supports/contradicts/neutral)
4. Delete low-confidence facts
5. Output compressed graph (3-10x compression)

## Input Format

From orchestrator with `CompressionRequest`:

```python
CompressionRequest(
    market_question="Will France win the World Cup 2026?",
    protected_terms=["France", "World Cup", "2026"],
    evidence_chunks=[
        EvidenceChunkMsg(
            source_type="sports_video",
            text='{"game": {"competitors": [{"team": "France", "score": 2}...]}}',
            source_url="https://espn.com/...",
            confidence=0.85
        )
    ],
    token_budget=200
)
```

## Output Format

**Text format (for decision agent):**
```
Q: Will France win the World Cup 2026?
YES: France dominated match 2-1 victory(0.55) | Odds favor France(0.75)
NO: Pogba questionable with ankle injury(0.85)
```

**JSON format (for analysis):**
```json
{
  "market": {
    "question": "Will France win the World Cup 2026?",
    "protected_terms": ["France", "World Cup", "2026"]
  },
  "facts": [
    {
      "text": "France 2-1 Brazil",
      "confidence": 0.95,
      "source_type": "sports_video",
      "relation_to_market": "supports",
      "relation_strength": 0.9
    }
  ],
  "summary": {
    "total_facts": 13,
    "supporting": 3,
    "contradicting": 2,
    "neutral": 8
  }
}
```

## Test Results

**Input:** 5 chunks with noisy JSON/HTML (169 tokens)
- ESPN JSON with game scores, injuries, odds
- Browserbase HTML scrape
- Kalshi market data JSON
- Plain text analysis

**Output:** Compressed text (30 tokens)

**Metrics:**
- ✅ **5.63x compression** achieved
- ✅ **13 facts extracted** from noisy data
- ✅ **3 JSON chunks parsed**
- ✅ **1 HTML chunk parsed**
- ✅ Market-centric: 1 YES, 2 NO facts

## Supported Source Types

### `sports_video`
Parses ESPN-style JSON:
- Game scores from competitors array
- Injury reports
- Betting odds and lines
- Team stats

### `financial_research`
Parses Kalshi-style JSON:
- Market prices (yes_price, no_price)
- Trading volume
- Price movements

### `culture_web`, `politics_news`
Parses HTML/text:
- Browserbase scrapes
- News article text
- Web search results

## Deployment

### Local Testing
```bash
python uagents_deploy/intelligent_compression_agent.py
```

### Agentverse Deployment
1. Run locally
2. Click Agent Inspector link
3. Connect → Mailbox → Finish
4. Discoverable on ASI:One!

## Integration with Orchestrator

```python
# Orchestrator workflow
async def process_market(ctx, market_question):
    # 1. Collect evidence from research agents
    sports_evidence = await ctx.send(sports_agent, EvidenceRequest(...))
    financial_evidence = await ctx.send(financial_agent, EvidenceRequest(...))

    # 2. Compress with intelligent compression
    compression_request = CompressionRequest(
        market_question=market_question,
        protected_terms=["France", "World Cup", "2026"],
        evidence_chunks=sports_evidence.evidence_chunks + financial_evidence.evidence_chunks,
        token_budget=200
    )

    compressed = await ctx.send(intelligent_compression_agent, compression_request)

    # 3. Send to decision agent
    decision = await ctx.send(decision_agent, DecisionRequest(
        market_question=market_question,
        compressed_context=compressed.compressed_context
    ))

    return decision
```

## Key Features

✅ **Real NLP** - Actually parses JSON/HTML/text, not just truncates
✅ **Market-centric** - Market question as central node
✅ **Intelligent** - Classifies fact-to-market relationships
✅ **High compression** - 3-10x compression achieved
✅ **Deduplication** - Merges similar facts
✅ **Quality filtering** - Removes low-confidence facts
✅ **Dual protocols** - Chat (ASI:One) + Custom (Orchestrator)
✅ **Production ready** - Full error handling, logging

## License

MIT License
