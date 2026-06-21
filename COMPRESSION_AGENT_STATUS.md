# Compression Agent - Current Status

## Active Agent

**ONLY graph_compression_agent is active and deployed**

### Agent Details
- **File**: [uagents_deploy/graph_compression_agent.py](uagents_deploy/graph_compression_agent.py)
- **Address**: `agent1qdmlp87fum7h3qwhtucc4smpx5nzkzzpkqlm98zn0h02yms46m7jg6hdvh2`
- **Port**: 8005
- **Mailbox**: Enabled (Agentverse deployed)

### Correct Implementation

✅ **One chunk = One node** (entire article as one node, not extracting multiple facts)
✅ **Merges redundant nodes** (same_sentiment relationship when overlap ≥60%)
✅ **Deletes low-value nodes** (keeps top 10 by score)
✅ **Creates relationship edges** (contradicts, reinforces, same_sentiment)
✅ **Outputs graph JSON** with nodes and edges

## Input Format

```json
{
  "request_id": "test-001",
  "market_id": "france-wc-2026",
  "market_question": "Will France win the World Cup 2026?",
  "evidence_chunks": [
    {
      "chunk_id": "espn_001",
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "<entire article text here>",
      "timestamp": "2026-06-20T12:00:00Z",
      "metadata": {...}
    }
  ],
  "token_budget": 200,
  "output_format": "json"
}
```

## Output Format

```json
{
  "nodes": [
    {
      "id": "espn_001",
      "source": "sports_video_agent",
      "text": "ESPN article about France...",
      "dir": "Y",
      "score": 0.75,
      "merged": 0
    }
  ],
  "edges": [
    {
      "from": "espn_001",
      "to": "kalshi_001",
      "type": "reinforces",
      "strength": 0.6
    }
  ]
}
```

## Test Files

- [test_graph_compression.py](test_graph_compression.py) - Main test script
- [test_graph_espn_input.json](test_graph_espn_input.json) - ESPN HTML test input

## Documentation

- [GRAPH_COMPRESSION_COMPLETE.md](GRAPH_COMPRESSION_COMPLETE.md) - Full implementation docs
- [uagents_deploy/GRAPH_COMPRESSION_README.md](uagents_deploy/GRAPH_COMPRESSION_README.md) - Agent README

## Archived Agents (Not Used)

The following agents were moved to `archived_agents/` folder:

- `intelligent_compression_agent.py` - WRONG implementation (extracted multiple facts per article)
- `standalone_compression_agent.py` - Old version
- `compression_agent.py` - Old version
- `compression_agent_advanced.py` - Old version

**Do not use these agents. They have the wrong implementation.**

## How to Use on ASI:One

1. Send message to agent address: `agent1qdmlp87fum7h3qwhtucc4smpx5nzkzzpkqlm98zn0h02yms46m7jg6hdvh2`
2. Use the input format above with your evidence chunks
3. Set `output_format: "json"` to get graph structure
4. Agent will respond with nodes and edges JSON

## Key Difference from Wrong Implementation

**Wrong (intelligent_compression_agent):**
- 1 ESPN article → 15 fact nodes ❌
- Extracts multiple facts from each article
- Not what research agents output

**Correct (graph_compression_agent):**
- 1 ESPN article → 1 node ✅
- Keeps article as single unit
- Merges/deletes/creates edges between articles
- Matches research agent output format

---

**Status**: ✅ graph_compression_agent is the only active compression agent
