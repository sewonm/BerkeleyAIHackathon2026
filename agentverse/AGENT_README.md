# SignalForge Market Research Agent

## Description

SignalForge is a compression-native multi-agent research engine for prediction markets.

A coordinator agent receives a sports or event market question, orchestrates specialized research sub-agents, compresses their raw outputs into a compact evidence packet, and returns an explainable simulated YES / NO / HOLD recommendation with probability estimate and confidence score.

## Capabilities

- Accepts sports and event prediction market questions in natural language
- Launches Browserbase-powered web research to gather current injuries, news, lineup updates, and form data
- Retrieves cached evidence and historical market context from Redis memory
- Compresses raw multimodal evidence (web, video, market, stats) into ranked evidence claims — typically 85–90% token reduction
- Estimates fair probability vs market-implied probability
- Calculates edge and generates a simulated YES / NO / HOLD recommendation
- Returns confidence score, supporting evidence, key uncertainties, and source attribution

## Example Input

```json
{
  "market_question": "Will Brazil beat Mexico in the 2026 FIFA World Cup?",
  "market_price": 0.61,
  "teams": ["Brazil", "Mexico"],
  "sport": "soccer"
}
```

## Example Output

```json
{
  "recommendation": "YES",
  "estimated_probability": 0.69,
  "market_probability": 0.61,
  "edge": 0.08,
  "confidence": "medium-high",
  "compression_ratio": "9.0x",
  "token_reduction_pct": 88.9,
  "top_evidence": [
    "Mexico's Lozano observed receiving physio treatment in warmup video.",
    "Brazil have won all 4 World Cup meetings against Mexico.",
    "xG model gives Brazil 63% win probability."
  ],
  "disclaimer": "Simulated research tool. Not financial advice."
}
```

## Sponsor Stack

| Layer | Technology |
|---|---|
| Agent discovery | Fetch AI Agentverse + Agent Chat Protocol |
| Web research | Browserbase Search + Fetch |
| Memory + cache | Redis (JSON, Streams, Sorted Sets) |
| Compression | Token Company — raw → compressed evidence packet |
| Decision LLM | Anthropic Claude |

## Disclaimer

This agent provides simulated paper-trading research only. It does not execute real-money trades, access live financial accounts, or provide financial advice. All recommendations are for educational and demonstration purposes only.

## How to Query via ASI:One

Send a natural language message such as:

```
Analyze this market: Will Brazil beat Mexico in the 2026 World Cup? Current YES price is 0.61.
```

The agent will return a full research summary with probability estimate and recommendation.
