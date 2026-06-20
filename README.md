# Multi-Agent Prediction Market Research with Context Compression

A multi-agent research and trading system for Kalshi-style prediction markets.

---

## 🚀 MVP Status

**Current Implementation: Local Text-Based Culture Evidence Pipeline**

This MVP demonstrates the core compression middleware using local sample data. The system runs entirely offline with no API keys required.

**What Works Now:**
- ✅ CultureWebAgent (reads from local sample file)
- ✅ Context compression middleware (scorer, deduplicator, protected terms)
- ✅ Deterministic decision agent
- ✅ Full pipeline with compression metrics
- ✅ Command-line demo

**Scaffolded for Future (Not Active):**
- 📋 SportsVideoAgent (placeholder)
- 📋 PoliticsNewsAgent (placeholder)
- 📋 FinancialResearchAgent (placeholder)
- 📋 MarketAgent (placeholder)
- 📋 Browserbase integration (service wrapper only)
- 📋 Kalshi integration (service wrapper only)
- 📋 Fetch.ai deployment (service wrapper only)
- 📋 LLM-based decision making (service wrapper only)

**To run the MVP:**

```bash
pip install -r requirements.txt
python -m app.main
```

**To run tests:**

```bash
pytest
```

The current MVP implements only the local text-based culture/web evidence pipeline. Other agents are scaffolded but not active yet.

---

## 🌐 Fetch.ai uAgents Deployment

**NEW: The system is now available as standalone Fetch.ai uAgents!**

Each functional component is deployed as an independent uAgent that can run on Agentverse:

- ✅ **OrchestratorAgent** - User-facing coordinator (Port 8000)
- ✅ **CultureWebAgent** - Evidence collector (Port 8001)
- ✅ **CompressionAgent** - Context compressor (Port 8002)
- ✅ **DecisionAgent** - Trading decision maker (Port 8003)

**To run uAgents locally:**

```bash
cd uagents_deploy

# Terminal 1
python culture_web_agent.py

# Terminal 2
python compression_agent.py

# Terminal 3
python decision_agent.py

# Terminal 4
python orchestrator_agent.py
```

**To deploy to Agentverse:**

See [AGENTVERSE_DEPLOYMENT.md](AGENTVERSE_DEPLOYMENT.md) for complete deployment instructions.

Each agent communicates via standardized message protocols and can be deployed, scaled, and updated independently.

---

The system coordinates specialized agents that collect evidence from web, video, news, financial, culture, and market sources. Their raw outputs are passed through a token-aware compression layer, which removes low-signal context and keeps decision-relevant evidence. A decision agent then estimates market edge and, when trading is enabled, routes approved trades to Kalshi through a gated execution layer.

```text
Raw evidence
    ↓
Specialized research agents
    ↓
Context compression middleware
    ↓
Compressed evidence packet
    ↓
Decision agent
    ↓
Risk manager
    ↓
Kalshi trade executor
```

## Core Idea

Prediction-market trading requires fast research across messy real-world information.

Useful signals can come from:

* news articles
* culture and entertainment coverage
* sports clips and transcripts
* financial reports
* political updates
* social media trends
* market prices and order books
* official announcements
* rumors and confirmations
* analyst commentary

A normal LLM workflow would pass large amounts of raw evidence into the model. This is expensive, slow, and noisy. Important signals can get buried under repeated articles, irrelevant text, scraped-page boilerplate, transcripts, and tool logs.

This project solves that by using specialized agents to collect evidence, then compressing their outputs into a smaller decision-ready context packet before final reasoning and trading.

## Token Company Compression Challenge

This project directly addresses the **Token Company Compression Challenge** by reducing the amount of context sent into LLM-based agents.

Instead of sending full articles, transcripts, scraped pages, and tool outputs into the final decision model, the system compresses raw agent outputs first.

The compression layer:

* removes low-signal filler
* deduplicates repeated claims
* keeps market-relevant evidence
* protects important names, dates, numbers, prices, and resolution criteria
* ranks evidence by decision relevance
* respects a configurable token budget
* reports token savings and compression ratio
* produces an auditable compressed evidence packet

The goal is to make multi-agent workflows faster, cheaper, and easier for an LLM to reason over.

## Agent System

The system is organized around specialized agents.

### Culture Web Agent

Collects evidence from culture, entertainment, streaming, music, box office, celebrity, and viral trend sources.

Example markets:

* Will a movie win Best Picture?
* Will an album debut at #1?
* Will a trailer reach a viewership milestone?
* Will a celebrity event happen before a deadline?

### Sports Video Agent

Analyzes sports clips, transcripts, press conferences, highlights, and injury-related evidence.

Example signals:

* player injury status
* coach statements
* lineup changes
* performance trends
* game footage observations
* broadcast commentary
* transcript-based evidence
* video-derived claims

### Politics News Agent

Researches political and public-event markets using news, polling, official statements, and current developments.

Example signals:

* polling changes
* candidate announcements
* court decisions
* regulatory updates
* public statements
* breaking news
* event deadlines

### Financial Research Agent

Analyzes macroeconomic, company, and market-related sources.

Example signals:

* inflation reports
* earnings updates
* Fed statements
* economic indicators
* market movements
* analyst expectations

### Market Agent

Connects Kalshi market data to the research pipeline.

Example signals:

* market title
* market ticker
* current YES / NO prices
* resolution criteria
* order book data
* price movement
* volume
* liquidity
* implied probability

### Decision Agent

Receives the compressed evidence packet and outputs:

* YES / NO / HOLD recommendation
* confidence score
* estimated fair probability
* estimated edge
* key evidence
* missing information
* reasoning summary

The decision agent does not directly place trades. It only produces a recommendation and probability estimate.

### Risk Manager

The risk manager decides whether a recommendation is allowed to become an actual trade.

It checks:

* trade mode
* live trading enabled flag
* confidence threshold
* minimum edge threshold
* max order size
* max number of orders
* market allowlist
* duplicate order protection
* available balance
* order side and price validity

### Trade Executor

The trade executor places approved orders on Kalshi.

It supports:

* dry-run mode
* demo mode
* live trading mode
* client order IDs
* order logging
* failed-order handling
* cancellation support
* trade result reporting

## Trading Modes

The system supports multiple execution modes.

### Dry Run Mode

Dry run mode simulates the trade without sending an order to Kalshi.

```text
TRADE_MODE=dry_run
ENABLE_LIVE_TRADING=false
```

Use this for testing the full pipeline safely.

### Demo Mode

Demo mode sends orders to Kalshi’s demo environment.

```text
TRADE_MODE=demo
KALSHI_ENV=demo
ENABLE_LIVE_TRADING=false
```

Use this for end-to-end testing with mock funds.

### Live Mode

Live mode sends real orders to Kalshi using production credentials.

```text
TRADE_MODE=live
KALSHI_ENV=production
ENABLE_LIVE_TRADING=true
```

In live mode, the system can place real trades. Live trading should only be enabled intentionally with production API credentials and configured risk limits.

## Trading Logic

The system compares the decision agent’s estimated fair probability against the current Kalshi market price.

Example:

```text
Market YES price: 0.42
Estimated fair probability: 0.55
Estimated edge: 0.13
Confidence: 0.76

Action: Buy YES
```

A trade is only allowed if it passes the risk manager.

Example requirements:

```text
confidence >= MIN_CONFIDENCE
edge >= MIN_EDGE
order_size <= MAX_ORDER_DOLLARS
market is allowed
live trading is explicitly enabled
```

If the edge is too small or confidence is too low, the system returns HOLD.

```text
Market YES price: 0.42
Estimated fair probability: 0.46
Estimated edge: 0.04
Confidence: 0.76

Action: HOLD
Reason: edge below threshold
```

## Compression Pipeline

The compression layer is the core technical component.

```text
Evidence chunks
    ↓
Protected term extraction
    ↓
Relevance scoring
    ↓
Deduplication
    ↓
Token-budget selection
    ↓
Compressed evidence packet
```

Each evidence chunk receives a keep score based on:

* relevance to the market question
* overlap with protected market terms
* presence of important entities
* presence of dates, prices, numbers, or deadlines
* source strength
* novelty compared to other chunks
* penalty for boilerplate, filler, or repeated content

The final output is a compact evidence packet that preserves the information most likely to affect the market decision.

## Example Output

```text
Market: Will Movie X win Best Picture?

Raw context tokens: 18,420
Compressed context tokens: 2,130
Compression ratio: 8.65x

Current YES price: 0.42
Estimated fair probability: 0.55
Estimated edge: 0.13

Recommendation: YES
Confidence: 0.76

Risk Check: Approved
Trade Mode: live
Trade Action: Buy YES
Order Size: $5.00

Key Evidence:
- Movie X received several major nominations.
- Critics have consistently ranked it among the top contenders.
- Box office performance is strong but not historically dominant.
- A competing film recently lost momentum after a major precursor award.

Missing Information:
- Final guild award results
- Updated market movement
- Official nomination list confirmation
```

## Repo Structure

```text
kalshi-agent-compression/
├── app/
│   ├── agents/
│   │   ├── coordinator.py
│   │   ├── culture_web_agent.py
│   │   ├── sports_video_agent.py
│   │   ├── politics_news_agent.py
│   │   ├── financial_research_agent.py
│   │   ├── market_agent.py
│   │   └── decision_agent.py
│   ├── compression/
│   │   ├── compressor.py
│   │   ├── scorer.py
│   │   ├── protected_terms.py
│   │   └── metrics.py
│   ├── trading/
│   │   ├── risk_manager.py
│   │   ├── trade_executor.py
│   │   └── order_logger.py
│   ├── schemas/
│   │   ├── evidence.py
│   │   ├── market.py
│   │   ├── compression.py
│   │   ├── decision.py
│   │   └── trade.py
│   ├── services/
│   │   ├── browserbase_service.py
│   │   ├── kalshi_service.py
│   │   ├── fetch_service.py
│   │   └── llm_service.py
│   └── utils/
│       ├── token_counter.py
│       ├── chunking.py
│       └── dedupe.py
├── examples/
│   ├── markets/
│   ├── raw_context/
│   └── outputs/
├── tests/
├── README.md
└── requirements.txt
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```bash
cp .env.example .env
```

Example environment variables:

```bash
# Kalshi
KALSHI_ENV=demo
KALSHI_BASE_URL=https://external-api.demo.kalshi.co/trade-api/v2
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PATH=

# Trading
TRADE_MODE=dry_run
ENABLE_LIVE_TRADING=false
MAX_ORDER_COUNT=1
MAX_ORDER_DOLLARS=5
MIN_CONFIDENCE=0.70
MIN_EDGE=0.05

# Optional services
BROWSERBASE_API_KEY=
OPENAI_API_KEY=
FETCH_API_KEY=
```

For live trading, update:

```bash
KALSHI_ENV=production
TRADE_MODE=live
ENABLE_LIVE_TRADING=true
```

Live trading requires valid production Kalshi credentials.

## How to Run

Run the system:

```bash
python -m app.main
```

Run tests:

```bash
pytest
```

The latest result is saved to:

```text
examples/outputs/latest_result.json
```

## Sponsor Integrations

### Browserbase

Browserbase powers live web research for agents that need to browse, search, and extract information from dynamic pages.

The system can use Browserbase for:

* culture research
* politics/news monitoring
* financial source browsing
* public web evidence collection

### Fetch.ai

Fetch.ai can be used to deploy the research system as a network of specialized agents.

Potential Fetch.ai agents:

```text
CultureWebAgent
SportsVideoAgent
PoliticsNewsAgent
FinancialResearchAgent
MarketAgent
CompressionAgent
DecisionAgent
RiskManagerAgent
TradeExecutionAgent
```

### Kalshi

Kalshi provides the prediction-market and trade-execution layer.

The system uses Kalshi for:

* market discovery
* current prices
* market metadata
* resolution criteria
* order book data
* account balance
* order placement
* order cancellation
* trade execution

The project supports real Kalshi trades when live trading is explicitly enabled.

### Token Company

The Token Company challenge is addressed through the compression middleware.

The system reduces the number of tokens passed from agent outputs into LLM reasoning steps while preserving market-critical evidence.

## Why This Matters

Multi-agent systems generate a lot of context. Each agent produces tool outputs, web results, transcripts, summaries, logs, and intermediate information. Passing all of that into a final LLM is expensive and can make reasoning worse because the important evidence gets buried.

This project compresses agent output into a smaller, cleaner, and more decision-relevant context packet.

That compressed packet is then used to make a trading decision and, when enabled, execute a real Kalshi trade.

The result is a prediction-market trading system that is:

* faster
* cheaper
* more interpretable
* easier to audit
* better suited for multi-agent workflows
* capable of real trade execution with risk controls

## Demo Goal

The demo shows the full trading loop:

```text
Select a Kalshi market
    ↓
Agents collect evidence
    ↓
Compression layer removes context bloat
    ↓
Decision agent estimates fair probability
    ↓
Risk manager approves or rejects trade
    ↓
Trade executor places Kalshi order
```

Main message:

**Noisy multi-agent research can be compressed into decision-ready market intelligence and routed into real Kalshi trades.**

## Disclaimer

This project is experimental software for hackathon and research purposes. Live trading can result in financial loss. Users are responsible for their own trading decisions, API keys, risk settings, and compliance with Kalshi’s rules and applicable laws.
