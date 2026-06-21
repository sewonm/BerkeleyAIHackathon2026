# Compression Agent - Correct Requirements

## Current Problems

1. **Not parsing noisy text** - Just truncating the `text` field, not extracting facts
2. **No market context** - Market question not in the graph
3. **Fake test data** - Using invented agent names instead of real evidence format

## What It Should Actually Do

### Input Format (Correct)

From orchestrator, receives evidence from research agents:

```python
CompressionRequest(
    market_question="Will France win the World Cup 2026?",
    protected_terms=["France", "World Cup", "2026"],
    evidence_chunks=[
        EvidenceChunkMsg(
            source_type="sports_video",  # From sports research agent
            text="<rough noisy text from ESPN API/scrape>France 2-1 Brazil...injury report...odds data...",
            source_url="https://espn.com/...",
            confidence=0.8,
            metadata={"fetched_via": "http", "kind": "scoreline"}
        ),
        EvidenceChunkMsg(
            source_type="financial_research",  # From financial agent
            text="<rough noisy text from financial API>Kalshi market data...volume...price movement...",
            source_url="https://kalshi.com/...",
            confidence=0.7,
            metadata={"fetched_via": "api"}
        )
    ]
)
```

### Processing Steps

#### 1. Parse Noisy Text → Extract Facts

**Input (rough noisy text):**
```
ESPN API Response: {"game": {"status": "final", "competitors": [{"team": "France", "score": 2}, {"team": "Brazil", "score": 1}]}, "injuries": [{"player": "Pogba", "status": "questionable"}], "odds": {"favorite": "France", "line": -150}}
```

**Output (extracted facts):**
```
Facts:
- "France defeated Brazil 2-1" (confidence: 0.9, source: ESPN game status)
- "Pogba questionable with injury" (confidence: 0.8, source: ESPN injury report)
- "Odds favor France at -150" (confidence: 0.7, source: ESPN odds)
```

#### 2. Build Graph with Market Question as Central Node

```
                    ┌─────────────────────────────┐
                    │   Market Question Node      │
                    │ "Will France win WC 2026?"  │
                    └─────────────────────────────┘
                              ↑        ↑        ↑
                  supports    │        │        │  contradicts
                             ↙         │         ↘
           ┌─────────────────┐  ┌─────────────┐  ┌──────────────────┐
           │ Fact Node 1     │  │ Fact Node 2 │  │ Fact Node 3      │
           │ France beat     │  │ Odds favor  │  │ Pogba injured    │
           │ Brazil 2-1      │  │ France      │  │ (questionable)   │
           │ (0.9 conf)      │  │ (0.7 conf)  │  │ (0.8 conf)       │
           └─────────────────┘  └─────────────┘  └──────────────────┘
                  ↑                    ↑                  ↑
            source: ESPN          source: ESPN      source: ESPN
```

#### 3. Create Relationship Edges

- **supports** - Fact suggests YES answer to market question
- **contradicts** - Fact suggests NO answer
- **neutral** - Fact is context but doesn't strongly suggest either way
- **reinforces** - Two facts support each other
- **conflicts** - Two facts contradict each other

#### 4. Compress via Deletion/Merging

- **Delete** low-confidence facts
- **Merge** redundant facts (e.g., "France won 2-1" + "France beat Brazil 2-1" → one fact)
- **Keep** high-value facts that strongly relate to market question

#### 5. Output Compressed Graph

**Text format:**
```
Market: Will France win the World Cup 2026?
YES: France defeated Brazil 2-1 (0.9) | Odds favor France (0.7)
NO: Key player Pogba injured (0.8)
Graph: 3 facts, 2 supporting, 1 contradicting
```

**JSON format:**
```json
{
  "market": {
    "question": "Will France win the World Cup 2026?",
    "protected_terms": ["France", "World Cup", "2026"]
  },
  "facts": [
    {
      "id": "f1",
      "text": "France defeated Brazil 2-1",
      "confidence": 0.9,
      "source_type": "sports_video",
      "source_url": "https://espn.com/...",
      "relation_to_market": "supports",
      "extracted_from_noisy": true
    },
    {
      "id": "f2",
      "text": "Pogba questionable with injury",
      "confidence": 0.8,
      "source_type": "sports_video",
      "relation_to_market": "contradicts",
      "extracted_from_noisy": true
    }
  ],
  "edges": [
    {"from": "f1", "to": "market", "type": "supports", "strength": 0.9},
    {"from": "f2", "to": "market", "type": "contradicts", "strength": 0.8}
  ]
}
```

## Key Algorithms Needed

### 1. Noisy Text Parser

```python
def parse_noisy_text(text: str, source_type: str) -> List[Fact]:
    """
    Parse rough noisy text (JSON, HTML, scraped data) into clean facts

    Handles:
    - JSON responses (ESPN API, Kalshi API)
    - HTML scrapes (Browserbase)
    - Search results
    - Raw text
    """
    facts = []

    # Try JSON parsing
    if is_json(text):
        facts.extend(extract_facts_from_json(text, source_type))

    # Try HTML parsing
    elif is_html(text):
        facts.extend(extract_facts_from_html(text))

    # Fall back to sentence extraction
    else:
        facts.extend(extract_facts_from_text(text))

    return facts
```

### 2. Fact Extraction

```python
def extract_facts_from_json(json_data: dict, source_type: str) -> List[Fact]:
    """Extract structured facts from JSON responses"""
    facts = []

    if source_type == "sports_video":
        # Extract from ESPN-style JSON
        if "game" in json_data:
            score = extract_score(json_data["game"])
            facts.append(Fact(text=score, confidence=0.9))

        if "injuries" in json_data:
            for injury in json_data["injuries"]:
                fact_text = f"{injury['player']} {injury['status']}"
                facts.append(Fact(text=fact_text, confidence=0.8))

    elif source_type == "financial_research":
        # Extract from Kalshi-style JSON
        if "market_price" in json_data:
            price = json_data["market_price"]
            facts.append(Fact(text=f"Market price: {price}", confidence=0.7))

    return facts
```

### 3. Fact-to-Market Relationship Classifier

```python
def classify_relationship(fact: Fact, market_question: str, protected_terms: List[str]) -> str:
    """
    Classify how a fact relates to the market question
    Returns: "supports", "contradicts", or "neutral"
    """
    # Check if fact contains positive signals
    positive_signals = ["won", "winning", "beat", "strong", "healthy", "favored"]
    negative_signals = ["lost", "injured", "weak", "questionable", "unlikely"]

    fact_lower = fact.text.lower()

    # Check relevance to protected terms
    relevance = sum(1 for term in protected_terms if term.lower() in fact_lower)

    if relevance == 0:
        return "neutral"

    # Classify based on signals
    yes_count = sum(1 for sig in positive_signals if sig in fact_lower)
    no_count = sum(1 for sig in negative_signals if fact_lower)

    if yes_count > no_count:
        return "supports"
    elif no_count > yes_count:
        return "contradicts"
    else:
        return "neutral"
```

## Implementation Plan

1. ✅ Fix data models to use real `EvidenceChunkMsg` format
2. ⏭️ Implement noisy text parser (JSON/HTML/text)
3. ⏭️ Implement fact extractor for each source_type
4. ⏭️ Add market question as central graph node
5. ⏭️ Implement fact-to-market relationship classifier
6. ⏭️ Build graph with facts pointing to market
7. ⏭️ Implement compression via deletion/merging
8. ⏭️ Test with real evidence from sports_video_agent

## Success Criteria

✅ Parses rough noisy text (JSON, HTML, raw) into clean facts
✅ Extracts 5-20 facts from typical evidence chunk
✅ Market question is central node in graph
✅ Each fact has edge to market (supports/contradicts/neutral)
✅ Achieves 2-5x compression
✅ Works with real evidence from sports/financial/culture agents
✅ Output is clean, readable, actionable for decision agent

---

**This is a complete rebuild - the current implementation is fundamentally wrong.**
