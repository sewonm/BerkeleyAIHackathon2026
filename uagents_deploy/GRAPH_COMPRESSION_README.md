# Graph Compression Agent 🗜️

![Innovation Lab](https://img.shields.io/badge/innovationlab-blue)
![Hackathon](https://img.shields.io/badge/hackathon-green)

**Agent Address:** `agent1q...` (derived from seed)

Compresses evidence from multiple sources into a compact graph with relationship analysis.

## What It Does

Takes evidence chunks from various sources (sports_video_agent, news_agent, odds_agent, etc.) and:

1. **Creates source nodes** - One node per evidence chunk
2. **Builds relationship edges** - Analyzes relationships between sources:
   - `contradicts` - Sources with opposite sentiment
   - `reinforces` - Sources supporting same conclusion
   - `same_sentiment` - Nearly identical sources (high semantic overlap)
3. **Merges redundant sources** - Combines sources with `same_sentiment` relationship
4. **Deletes low-value sources** - Removes sources with low information value
5. **Reinforces clusters** - Boosts scores of sources in high-agreement clusters
6. **Outputs compressed graph** - Returns compact representation

## Dual Protocol Support

### 1. Chat Protocol (ASI:One)

Test directly in ASI:One chat interface!

**Input format:**
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "evidence_chunks": [
    {
      "chunk_id": "1",
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France defeated Brazil 2-1 in yesterday's match. Mbappe scored twice."
    },
    {
      "chunk_id": "2",
      "market_id": "france-wc-2026",
      "source_agent": "odds_agent",
      "source_type": "betting_odds",
      "text": "Current betting odds favor France at 62% implied probability."
    }
  ],
  "token_budget": 200,
  "output_format": "text"
}
```

**Output format (`"text"`):**
```
YES:France defeated Brazil 2-1 in yesterday's match(0.85)|Current betting odds favor France at 62% implied(0.72)
```

**Output format (`"json"`):**
```json
{
  "nodes": [
    {"id":"1","source":"sports_video_agent","text":"France defeated Brazil 2-1...","dir":"Y","score":0.85,"merged":0},
    {"id":"2","source":"odds_agent","text":"Current betting odds favor France...","dir":"Y","score":0.72,"merged":0}
  ],
  "edges": [
    {"from":"1","to":"2","type":"reinforces","strength":0.7}
  ]
}
```

### 2. Custom Protocol (Orchestrator)

For agent-to-agent communication:

```python
from graph_compression_agent import CompressionRequest, EvidenceChunk

request = CompressionRequest(
    market_id="test",
    market_question="Will France win?",
    evidence_chunks=[...],
    token_budget=200,
    output_format="text"
)

response = await ctx.send(compression_agent_address, request)
# response.compressed_output contains the result
# response.metrics contains compression statistics
```

## Input Format

### Required Fields

Each evidence chunk must have:
- `chunk_id` - Unique identifier
- `market_id` - Market identifier
- `source_agent` - Agent that provided this evidence (e.g., "sports_video_agent")
- `source_type` - Type of source (e.g., "sports_video", "news", "betting_odds")
- `text` - The evidence text

### Optional Fields

- `timestamp` - When the evidence was collected
- `metadata` - Additional metadata about the source

## How It Works

### Step 1: Create Source Nodes

Each evidence chunk becomes a node:
```
Node 1: sports_video_agent → "France beat Brazil 2-1"
Node 2: news_agent → "France defeated Brazil 2-1"
Node 3: odds_agent → "France odds 62%"
```

### Step 2: Build Relationship Edges

Analyzes text similarity and sentiment:
```
Node 1 ←same_sentiment→ Node 2 (90% overlap)
Node 1 ←reinforces→ Node 3 (same YES direction)
```

### Step 3: Merge Similar Sources

Nodes with `same_sentiment` relationship are merged:
```
Node 1 + Node 2 → Node 1 (keep higher score)
```

### Step 4: Delete Low-Value Sources

Keeps only top N sources by information value.

### Step 5: Reinforce Clusters

Boosts scores of sources with many `reinforces` edges.

### Step 6: Generate Output

**Text format:**
```
YES:France beat Brazil 2-1(0.85)|France odds 62%(0.72)
```

**JSON format:**
```json
{
  "nodes": [...],
  "edges": [...]
}
```

## Information Value Scoring

Each source is scored (0.0-1.0) based on:
- **Numbers/Stats** (+0.3) - Quantitative data
- **Signal words** (+0.3) - "won", "lost", "injured", etc.
- **Named entities** (+0.2) - Proper nouns
- **Strong direction** (+0.1) - Clear YES/NO sentiment
- **Text length** (+0.1) - Optimal 20-100 words

## Compression Metrics

Returns:
- `raw_tokens` - Input token count
- `compressed_tokens` - Output token count
- `compression_ratio` - How much compression achieved (e.g., 3.0x)
- `initial_sources` - Number of input chunks
- `merged_sources` - How many sources were merged
- `deleted_sources` - How many sources were deleted
- `final_sources` - Number of sources in output
- `relationships` - Number of edges in graph
- `yes_sources` - Sources supporting YES
- `no_sources` - Sources supporting NO

## Example Workflow

**Input (3 sources, 150 tokens):**
```
1. "France defeated Brazil 2-1 in thrilling match yesterday. Mbappe scored twice..."
2. "France beat Brazil 2-1. Mbappe's performance was exceptional..."
3. "Betting odds favor France at 62% implied probability. Market shifted 5%..."
```

**Processing:**
1. Create 3 nodes
2. Find edges: 1 ←same_sentiment→ 2, 1 ←reinforces→ 3
3. Merge: Node 1 + Node 2 → Node 1
4. Score: Node 1 (0.85), Node 3 (0.72)
5. Output: 2 nodes, 1 edge

**Output (50 tokens, 3.0x compression):**
```
YES:France defeated Brazil 2-1. Mbappe scored twice(0.85)|Betting odds favor France at 62%(0.72)
```

**Metrics:**
```json
{
  "raw_tokens": 150,
  "compressed_tokens": 50,
  "compression_ratio": 3.0,
  "initial_sources": 3,
  "merged_sources": 1,
  "deleted_sources": 0,
  "final_sources": 2,
  "relationships": 1
}
```

## Deployment

### Local Testing
```bash
python uagents_deploy/graph_compression_agent.py
```

### Agentverse Deployment
1. Run the agent locally
2. Open Agent Inspector link in terminal
3. Connect → Mailbox → Finish
4. Agent is now discoverable on ASI:One!

## Integration

### With Orchestrator
```python
# Orchestrator collects evidence from multiple agents
sports_evidence = await ctx.send(sports_agent, EvidenceRequest(...))
news_evidence = await ctx.send(news_agent, EvidenceRequest(...))
odds_evidence = await ctx.send(odds_agent, EvidenceRequest(...))

# Compress all evidence
compression_request = CompressionRequest(
    market_question="Will France win?",
    evidence_chunks=[sports_evidence, news_evidence, odds_evidence],
    token_budget=200
)

compressed = await ctx.send(compression_agent, compression_request)

# Send compressed output to decision agent
decision = await ctx.send(decision_agent, compressed.compressed_output)
```

## Configuration

Environment variables:
- `GRAPH_COMPRESSION_AGENT_SEED` - Agent seed (keep constant!)

## License

MIT License
