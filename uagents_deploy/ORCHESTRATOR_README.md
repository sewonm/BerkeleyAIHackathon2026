# Quorum Orchestrator Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:prediction-markets](https://img.shields.io/badge/prediction--markets-FF8C00)

The **front door** for prediction-market questions. Send it a messy natural-language market question and it routes the query to the right specialized research agent, then returns the routing decision plus the collected evidence analysis.

## What it does

1. **Classifies + rewrites** your question into a focused research request (LLM tier via ASI:One, with a never-fail keyword heuristic fallback).
2. **Routes** to exactly one specialized agent by category:
   - **sports** → Sports Agent (live ESPN stats, odds, win-prob, injuries/lineups)
   - **financial** → Financial Research Agent
   - **culture** → Culture/Web Agent
   - **politics / other** → graceful "no live agent wired yet" handoff
3. **Replies** with a routing note (category, tier, confidence, rationale) so the decision is observable, then dispatches a single evidence request downstream.

## How to use

Just ask a market question in plain language, for example:

- "Will Argentina win the 2026 World Cup?"
- "Is Bitcoin going to close above $100k this month?"
- "Will this movie top the box office opening weekend?"

You'll get back the routing decision and, when the downstream agents are live, the evidence-backed analysis.

## Agent Address

```
agent1qwnc0kf3npdvhqlw4dtmj6ejfnpnaek9y7hrywqunwmm9v9rum8pq59jxgm
```

This address is derived from the fixed seed in `ORCHESTRATOR_AGENT_SEED` and is stable across restarts.

## Tags

The `innovationlab` and `hackathon` tags are applied via the shields.io badges at the top of this README — Agentverse derives an agent's marketplace tags from its README badges (not from a separate UI field).

## Protocol

**Chat Protocol v0.3.0** (ASI:One discoverable, `publish_manifest=True`).
