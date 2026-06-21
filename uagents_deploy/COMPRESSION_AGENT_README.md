# Quorum Compression Agent

![tag:innovationlab](https://img.shields.io/badge/tag-innovationlab-blue) ![tag:hackathon](https://img.shields.io/badge/tag-hackathon-green) ![domain:prediction_markets](https://img.shields.io/badge/domain-prediction__markets-orange)

Given raw evidence chunks from upstream collectors (sports, financial, web), this agent compresses the context using graph-consensus algorithms with information-theoretic scoring, extracting high-signal claims and detecting contradictions — ready for a downstream decision engine.

Context-agnostic (works with sports, finance, politics, culture evidence). Each compression result includes:

- **Claim extraction** — Identifies key factual statements from raw text using heuristic and Claude-based extraction
- **Graph construction** — Builds evidence graph with nodes (claims, entities, sources) and edges (supports, opposes, conflicts)
- **Consensus clustering** — Groups similar claims using semantic similarity and assigns consensus scores
- **Information-value scoring** — Ranks claims by market impact, probability shift, and confidence
- **Contradiction detection** — Identifies conflicting evidence using graph analysis
- **Token reduction** — Compresses typical 400+ token bundles down to ~150 tokens (2-3x compression)

## Agent Address

```
<deploy to get address>
```

This address is derived from the fixed seed `compression_agent_standalone_seed_change_in_production` and is stable across all restarts.

## Tags

The `innovationlab` and `hackathon` tags are applied via the shields.io badges at the top of this README — Agentverse derives an agent's marketplace tags from its README badges (not from a separate UI field).

## Protocol

### Chat Protocol v0.3.0 (ASI:One discoverable)

This agent uses the standard uAgents Chat Protocol v0.3.0, making it directly reachable from ASI:One and the Agentverse chat UI.

### Custom Protocol: StandaloneContextCompression

For orchestrator-to-agent machine-to-machine communication.

## Input

### Via Chat (ASI:One / Agentverse UI)

**Demo mode** — Type one of:
```
@compression-agent demo
@compression-agent test
@compression-agent example
```

**IMPORTANT:** The compression agent expects a **request wrapper** containing an array of evidence chunks, NOT a single evidence chunk.

### Sports Video Agent Output → Compression Agent Input

**What sports_video_agent outputs (single chunk):**
```json
{
  "source_type": "sports_video",
  "text": "France 2-1 Brazil (Final). Goals from Mbappe (23', 67')...",
  "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/...",
  "confidence": 0.95,
  "metadata": {
    "kind": "score_state",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447"
  }
}
```

**What compression agent expects (request with array of chunks):**
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "evidence_chunks": [
    {
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France 2-1 Brazil (Final). Goals from Mbappe (23', 67')...",
      "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/...",
      "confidence": 0.95,
      "metadata": {
        "kind": "score_state",
        "sport": "soccer",
        "league": "fifa.world",
        "event_id": "760447"
      }
    }
  ]
}
```

**Key differences:**
- Compression agent needs `market_question` wrapper
- Evidence chunks must be in an `evidence_chunks` array
- Each chunk needs `market_id` and `source_agent` fields added
- Sports agent output → Add to array → Wrap in request

**JSON mode** — Full example with multiple chunks from sports agent:
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "evidence_chunks": [
    {
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France defeated Brazil 2-1 in their recent match. Goals from Mbappe (23', 67') and Neymar for Brazil (45+2'). Attendance: 88,966 at Lusail Stadium.",
      "source_url": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=760447",
      "confidence": 0.95,
      "metadata": {
        "kind": "score_state",
        "sport": "soccer",
        "league": "fifa.world"
      }
    },
    {
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "Betting odds: France -120 (45.5% implied), Brazil +150. Win probability model: France 52%, Brazil 31%, Draw 17%. Line movement: France opened at -110, moved to -120 (increased 9% in last 24h).",
      "confidence": 0.88,
      "metadata": {
        "kind": "odds"
      }
    },
    {
      "market_id": "france-wc-2026",
      "source_agent": "sports_video_agent",
      "source_type": "sports_video",
      "text": "France: Kylian Mbappe (Healthy), Antoine Griezmann (Healthy), N'Golo Kante (Questionable - ankle). Brazil: Neymar (Probable - minor knock), Vinicius Jr (Healthy), Casemiro (Out - suspended).",
      "confidence": 0.92,
      "metadata": {
        "kind": "injuries"
      }
    }
  ],
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "aggressiveness": 0.5
}
```

**Required fields:**
- `market_question` (string) — The prediction market question
- `evidence_chunks` (array) — List of evidence chunks, each with:
  - `market_id` (string) — Market identifier
  - `source_agent` (string) — Which agent collected this evidence
  - `source_type` (string) — Type of evidence (sports_video, financial_research, culture_web, etc.)
  - `text` (string) — **The raw evidence content**

**Optional fields:**
- `resolution_criteria` (string) — How the market resolves
- `current_yes_price` (float, 0.0-1.0) — Current YES market price
- `current_no_price` (float, 0.0-1.0) — Current NO market price
- `aggressiveness` (float, 0.0-1.0) — Compression level (0.0 = keep all, 1.0 = only top items, default 0.5)

For each evidence chunk:
- `source_url` (string, optional) — URL where evidence was found
- `timestamp` (string, optional) — When evidence was collected
- `confidence` (float, optional) — Confidence in evidence (0.0-1.0, default 0.8)
- `metadata` (dict, optional) — Additional metadata

### Via Custom Protocol (Orchestrator)

The agent accepts `EnhancedCompressionRequest` messages with the same structure as the JSON input above.

## Output

### Acknowledgement
A `ChatAcknowledgement` sent immediately on receipt (ack-first pattern).

### Compression Result

**Via Chat:** A `ChatMessage` with formatted compression results.

**Example output:**
```
Demo Compression Complete 🗜️

Input:
- Market: Will France win the World Cup 2026?
- Evidence chunks: 5
- Aggressiveness: 0.5

Compression Metrics:
- Raw tokens: 450
- Compressed tokens: 180
- Compression ratio: 2.5x
- Claims extracted: 8
- Consensus items: 5

Top YES Evidence (3 items):
• France defeated Brazil 2-1 in their most recent match with strong performance
• Betting markets favor France at 52% win probability vs Brazil's 31%
• Key offensive players Mbappe and Griezmann are healthy and in good form

Top NO Evidence (2 items):
• N'Golo Kante is questionable with an ankle injury creating defensive uncertainty
• Limited information on tournament stage and specific opponent

Contradictions Found: 0
(None detected - evidence is consistent)

Compressed Context Preview:
```
MARKET: Will France win the World Cup 2026?

TOP YES EVIDENCE (62% confidence):
• France defeated Brazil 2-1 with goals from Mbappe
• Betting odds favor France at 52% implied probability
• Key players Mbappe and Griezmann healthy

TOP NO EVIDENCE (38% confidence):
• Kante questionable with ankle injury
• Tournament stage unclear

CONSENSUS: France shows strong form but injury concerns create uncertainty
```
```

### Via Custom Protocol

Returns `EnhancedCompressionResponse` containing:

```python
{
  "request_id": "uuid",
  "market_id": "france-wc-2026",
  "status": "success",
  "compression_result": {
    "compressed_context": "<formatted text for decision agent>",
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
        "canonical_claim": "France won 2-1 against Brazil",
        "supporting_chunks": 2,
        "consensus_score": 0.95,
        "direction": "YES"
      }
    ],
    "top_opposing_evidence": [
      {
        "canonical_claim": "Kante questionable with ankle injury",
        "supporting_chunks": 1,
        "consensus_score": 0.75,
        "direction": "NO"
      }
    ],
    "contradictions": [],
    "missing_info": ["Tournament stage not specified", "Opponent unknown"]
  }
}
```

The `compressed_context` is a formatted string ready for the decision agent, containing:
- Market question
- Top YES evidence ranked by information value
- Top NO evidence ranked by information value
- Detected contradictions (if any)
- Missing information gaps
- Consensus summary

## Example Questions

**Sports:**
```
Evidence about "Will France win the World Cup?" with ESPN stats, odds, injuries
```

**Financial:**
```
Evidence about "Will Bitcoin reach $100k?" with market data, news, sentiment
```

**Culture:**
```
Evidence about "Will the new Marvel movie break records?" with reviews, box office, social media
```

## Run / Deploy (Mailbox)

```bash
# from the repo root
python uagents_deploy/standalone_compression_agent.py

# open the printed Agent Inspector link -> Connect -> Mailbox -> Finish
# (registers it on Agentverse + ASI:One; the address stays stable)
```

## Try it from ASI:One

1. Go to https://asi1.ai and search for this agent by name (`compression_agent_standalone`) or address
2. Send a test command: `@compression-agent demo`
3. You receive an ack, then a formatted compression result with metrics

## Architecture Notes

- **Dual-protocol**: Chat Protocol v0.3.0 (ASI:One / human chat) + custom `StandaloneContextCompression` protocol (orchestrator machine-to-machine)
- **Fixed seed / stable address**: The agent address never changes while the seed constant is unchanged
- **Mailbox agent**: Runs locally with `mailbox=True`; deploy via Agent Inspector (Connect → Mailbox)
- **Ack-first**: Acknowledges immediately, then processes compression
- **Graph-consensus algorithm**: Builds evidence graph, clusters similar claims, ranks by information value
- **Claude-powered (optional)**: Uses Claude for claim extraction if `ANTHROPIC_API_KEY` is set; falls back to heuristics otherwise
- **@mention aware**: Strips `@compression-agent` prefix from chat messages for ASI:One compatibility

## Compression Pipeline

1. **Claim Extraction** — Parses raw evidence chunks into structured claims (entities, dates, numbers, direction)
2. **Graph Construction** — Builds nodes (claims, entities, sources) and edges (supports, opposes, conflicts)
3. **Consensus Clustering** — Groups semantically similar claims using cosine similarity
4. **Information Scoring** — Ranks claims by market impact and probability shift
5. **Contradiction Detection** — Identifies conflicts using graph traversal
6. **Context Formatting** — Outputs compressed context optimized for decision agent consumption

## Integration

**Upstream:** Receives evidence from sports_video_agent, financial_research_agent, culture_web_agent

**Downstream:** Sends compressed context to decision_agent_standalone

**Orchestrator:** Called by orchestrator_agent.py as part of the full prediction market analysis pipeline

## Configuration

- `ANTHROPIC_API_KEY` (optional) — For Claude-powered claim extraction (falls back to heuristics)
- Port: 8002 (configurable via `AGENT_PORT`)
- Seed: Set via `AGENT_SEED` environment variable for production

---

**Last Updated:** 2026-06-20
**Status:** ✅ Production Ready
**Agent Type:** Mailbox Agent (Local deployment with Agentverse registration)
