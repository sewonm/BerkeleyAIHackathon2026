# SignalForge — Project Context for Claude

## One-liner
SignalForge is a compression-native multi-agent research engine for prediction markets that converts video, web, and market signals into compressed evidence packets and explainable simulated YES/NO/HOLD recommendations.

## Repo
https://github.com/sewonm/BerkeleyAIHackathon2026
Adam's branch: `adam/product-layer`

---

## Team

| Person | Role | Owns |
|---|---|---|
| **Adam** (me) | Data science / product / sponsor / pitch | Sponsor mapping, README, pitch, demo script, probability framing, Redis contract, Browserbase spec, Agentverse profile, UI requirements |
| **Vepaul** | Backend / orchestration lead | FastAPI backend, coordinator agent, `/analyze-market` endpoint, pipeline wiring, Agentverse deployment |
| **Sewon** | Math/CS — compression + decision logic | Compression scoring, claim ranking, token metrics, probability calibration, edge calculation, YES/NO/HOLD logic |
| **Derek** | CS — implementation | Video-to-text pipeline, Browserbase web agent wiring, market data parser, frontend/backend glue |

---

## Architecture

```
ASI:One / Agentverse
        ↓
SignalForge Main Agent (agentverse/agent_wrapper.py, port 8001)
        ↓
FastAPI Backend /analyze-market (app/main.py, port 8000)
        ↓
Coordinator Agent (app/agents/coordinator.py)
        ↓
┌─────────────────────────────────────────────┐
│ Browserbase Research Agent (port 3001, TS)  │ → web claims
│ Video Agent (Derek)                         │ → frame claims
│ Stats Agent                                 │ → stats claims
│ Market Agent                                │ → Kalshi snapshot
└─────────────────────────────────────────────┘
        ↓
Redis (app/services/redis_service.py)
  market:{id}:claims       ← all agents append here
  market:{id}:snapshot     ← market_agent writes
  market:{id}:compressed   ← compression_agent writes
  market:{id}:decision     ← decision_agent writes
        ↓
Compression Agent (Sewon)
        ↓
Compressed Evidence Packet
        ↓
Decision Agent — Claude API (Sewon / Vepaul)
        ↓
YES / NO / HOLD + probability + edge + explanation
        ↓
Frontend
```

---

## Demo Market

**Sport: Soccer — FIFA World Cup 2026** (currently happening, June–July 2026)
**Demo question:** "Will Brazil beat Mexico in the 2026 FIFA World Cup?"

```json
{
  "market_question": "Will Brazil beat Mexico in the 2026 FIFA World Cup?",
  "yes_price": 0.61,
  "implied_probability": 0.61,
  "teams": ["Brazil", "Mexico"],
  "sport": "soccer"
}
```

Demo output target:
- Estimated probability: 69%
- Market probability: 61%
- Edge: +8%
- Recommendation: YES
- Compression: ~89% token reduction
- Disclaimer: "Simulated research tool. Not financial advice."

---

## Sponsor Mapping

| Sponsor | What we use | Key pitch line |
|---|---|---|
| **Browserbase** | Web research sub-agent (Search + Fetch APIs → structured claims) | "Browserbase powers live web research — not a scraper, an agent" |
| **Fetch AI / Agentverse** | Main agent registered on Agentverse via Agent Chat Protocol; discoverable on ASI:One | "ASI:One finds and calls our agent; our backend does the real work" |
| **Token Company** | Compression layer reduces raw evidence ~89% before final LLM | Show: 34,400 raw tokens → 3,820 compressed → 89% reduction |
| **Redis** | Agent memory: claims cache, market snapshots, event streams, leaderboard | "Beyond caching: agent memory + vector context + real-time streams" |
| **Anthropic** | Claude as decision/explanation LLM; Claude Code used to build system | Explicitly say Claude Code built the system |
| **Interaction Co** | Automated multi-agent research workflow | Secondary only |

---

## Files Already Built (adam/product-layer)

```
.env.example                              ← all env vars documented
browserbase-agent/
  package.json                            ← npm deps (@browserbasehq/sdk, express)
  tsconfig.json
  browserbaseResearchAgent.ts             ← Search + Fetch → claims (with mock fallback)
  server.ts                               ← Express on port 3001, POST /browserbase-research
app/
  agents/
    coordinator.py                        ← orchestrates all agents, writes to Redis
  services/
    browserbase_service.py               ← Python Browserbase wrapper (for Derek)
    redis_service.py                     ← all Redis read/write functions
agentverse/
  agent_wrapper.py                       ← ASI:One compatible agent (correct ACP protocol)
  AGENT_README.md                        ← Agentverse profile text
examples/
  markets/world_cup_match.json           ← demo market data (Brazil vs Mexico)
  raw_context/sample_web_evidence.json   ← fake web chunks, 24,800 raw tokens
  raw_context/sample_video_evidence.json ← fake frame observations
  raw_context/sample_stats.json          ← H2H, xG, injury data
  outputs/sample_output.json             ← expected full pipeline output
  redis/contract.json                    ← Redis key schema contract
```

---

## What Still Needs Building

**Vepaul:**
- `app/main.py` — FastAPI app + `POST /analyze-market` endpoint
- Wire coordinator to real compression (replace `_mock_compress`)
- Wire coordinator to real decision agent (replace `_mock_decision`)
- Run ngrok on port 8001 for Agentverse registration

**Sewon:**
- `app/compression/compressor.py` — real scoring formula:
  `claim_score = relevance*0.4 + confidence*0.3 + recency*0.2 + source_quality*0.1`
- `app/compression/token_counter.py` — tiktoken-based raw vs compressed count
- Probability calibration + edge calc + YES/NO/HOLD logic
- Replace `_mock_compress` and `_mock_decision` in coordinator.py

**Derek:**
- Wire `browserbase-agent/` TypeScript server (just `npm install && npx ts-node server.ts`)
- Build video-to-text pipeline → frame sampling → Claude Vision → claims
- Market data parser

**Adam (me):**
- `requirements.txt` — pin all Python deps
- Updated `README.md` — sponsor mapping, architecture, setup instructions
- Frontend UI spec (sections below)
- Demo script (90 seconds)
- Register agent on Agentverse (need Vepaul's ngrok URL first)
- Add Agentverse + ASI:One promo codes: `BERKELEYAIAV` / `BERKELEYAI`

---

## Shared Claim Schema (everyone uses this exact format)

```json
{
  "claim": "Specific evidence statement",
  "source_type": "video | web | market | stats",
  "source_name": "ESPN article, Kalshi orderbook, etc.",
  "supports": "yes | no | hold | neutral",
  "confidence": 0.82,
  "market_relevance": 0.91,
  "recency": "high | medium | low",
  "raw_evidence": "short quote or observation",
  "raw_tokens": 1200,
  "compressed_tokens": 140
}
```

---

## Redis Key Schema (do not invent new keys)

```
market:{market_id}:snapshot     ← market_agent writes (Kalshi price, volume)
market:{market_id}:claims       ← APPEND ONLY — all agents write here
market:{market_id}:compressed   ← compression_agent writes
market:{market_id}:decision     ← decision_agent writes
game:{game_id}:state            ← live score/clock
game:{game_id}:stats:{entity}   ← player/team stats
stream:game:{game_id}:events    ← Redis Stream (live events)
user:{user_id}:portfolio        ← paper trading
leaderboard:paper_trading       ← sorted set, score = PnL
```

MVP: only the first 4 keys matter.

---

## Browserbase API (confirmed from real docs)

```python
from browserbase import Browserbase
bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])

# Step 1: Search (no browser, cheap)
results = bb.search.web(query="Brazil Mexico injury report", num_results=5)

# Step 2: Fetch as markdown (no browser, cheap)
page = bb.fetch_api.create(url=results[0].url, format="markdown")
print(page.content)

# Install: pip install browserbase>=1.11.0
# No Stagehand needed for our use case
```

---

## Agentverse / ASI:One Setup (confirmed from docs)

```python
# Correct pattern — uses chat_protocol_spec (NOT custom Model classes)
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, EndSessionContent, chat_protocol_spec
)
from uagents import Agent, Protocol

agent = Agent(
    name="signalforge-market-research",
    seed=AGENT_SEED,       # REQUIRED for stable address
    port=8001,
    mailbox=True,          # REQUIRED for Agentverse discoverability
    publish_agent_details=True,
)
protocol = Protocol(spec=chat_protocol_spec)

# pip install uagents uagents-core
# Run: python agentverse/agent_wrapper.py
# → prints stable agent address → paste into Agentverse registration
# → expose via ngrok: ngrok http 8001
```

Promo codes to activate before demo:
- Agentverse: `BERKELEYAIAV` at agentverse.ai
- ASI:One: `BERKELEYAI` at asi1.ai

---

## FastAPI Endpoint Contract (Vepaul builds this)

```
POST /analyze-market
Content-Type: application/json

Input:
{
  "market_question": "Will Brazil beat Mexico in the 2026 FIFA World Cup?",
  "market_price": 0.61,
  "teams": ["Brazil", "Mexico"],
  "sport": "soccer",
  "market_id": "kalshi_bra_mex_wc2026",
  "video_path": null
}

Output:
{
  "market_id": "kalshi_bra_mex_wc2026",
  "compression_metrics": {
    "raw_context_tokens": 34400,
    "compressed_tokens": 3820,
    "compression_ratio": "9.01x",
    "token_reduction_pct": 88.9
  },
  "decision": {
    "market": "Will Brazil beat Mexico in the 2026 FIFA World Cup?",
    "estimated_probability": 0.69,
    "market_probability": 0.61,
    "edge": 0.08,
    "recommendation": "YES",
    "confidence": "medium-high",
    "reasoning": ["..."],
    "risks": ["..."],
    "disclaimer": "Simulated research tool. Not financial advice."
  }
}
```

---

## Frontend UI Sections (for whoever builds UI)

1. **Market selector** — market question, sport, game time
2. **Agent activity cards** — one card per agent (Video / Web / Market / Stats), status + claim count
3. **Raw vs compressed evidence** — side by side, token counts
4. **Compression metrics** — raw tokens, compressed tokens, reduction %, latency
5. **Decision panel** — big YES/NO/HOLD, probability bar, edge, confidence
6. **Evidence list** — top 3–5 claims with source badges
7. **Disclaimer footer** — always visible: "Simulated research tool. Not financial advice."

---

## Build Order

```
Phase 1 — Mock pipeline end-to-end (do first)
  Vepaul: FastAPI + coordinator + mock compression + mock decision → /analyze-market works

Phase 2 — Real compression (Sewon)
  Replace _mock_compress() with real scorer
  Replace _mock_decision() with Claude API call
  Show real token reduction numbers

Phase 3 — Real Browserbase (Derek)
  npm install in browserbase-agent/
  npx ts-node server.ts
  Set BROWSERBASE_API_KEY

Phase 4 — Real video (Derek)
  Frame sampling + Claude Vision → claims
  Most expensive, do last

Phase 5 — Agentverse (Adam + Vepaul)
  Vepaul: ngrok http 8001
  Adam: register on Agentverse with ngrok URL + AGENT_README.md text
  Test: send a ChatMessage via ASI:One
```

---

## Key Rules

- Never pass raw articles/transcripts to the final LLM — compressed packet only
- `market:{id}:claims` is append-only — agents add to it, never overwrite
- Everyone outputs claims in the shared schema above — no free-form summaries
- All trading is paper/simulated — `ENABLE_LIVE_TRADING=false` always during demo
- Disclaimer on every output: "Simulated research tool. Not financial advice."
- Do not fake sponsor integrations — only claim what's actually running

---

## 90-Second Demo Script

1. "We selected a World Cup market on Kalshi — Will Brazil beat Mexico? YES at 61 cents."
2. "Our coordinator agent launches four specialized research agents simultaneously."
3. "The Browserbase web agent searches for injuries, form, and news — returns structured claims."
4. "The video agent analyzes a pregame clip — flags Lozano receiving physio treatment."
5. "The stats agent adds H2H data: Brazil W4/4 in World Cup vs Mexico."
6. "Raw evidence: 34,400 tokens across all sources."
7. "Our compression agent reduces that to 3,820 tokens — 89% reduction — while preserving every decision-critical signal."
8. "The decision agent sees only the compressed packet. It estimates Brazil's true probability at 69% vs 61% implied — an 8-point edge."
9. "Recommendation: Simulated YES. Confidence: medium-high."
10. "This entire pipeline is discoverable on Fetch AI Agentverse. Any ASI:One user can query our agent."
11. "Simulated research tool. Not financial advice."
