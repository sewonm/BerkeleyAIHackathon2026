# Quorum Culture/Web Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:culture](https://img.shields.io/badge/culture-FF6F61)

Given a Kalshi **culture / entertainment** market question (awards, box office, streaming, music charts, celebrity), this agent searches the **live web** and returns a raw **evidence bundle** as `EvidenceChunk`s — ready for a downstream compression engine.

**Domain-agnostic** within culture: it fans the market question out across several search intents (headline / latest-news / prediction-odds) and blends results from two providers:

- **Serper.dev (preferred)** — Google search results returned as clean JSON (title + link + snippet).
- **Browserbase** — DuckDuckGo HTML rendered through a real browser (no bot blocking), plus per-URL page render to markdown so each hit is enriched with the actual article body.

Each hit is de-duplicated by URL and enriched with up to ~2 KB of rendered page text, yielding several raw chunks per query.

## Agent Address

```
agent1qvs3g4c8npcz26tzra7cwfh3652x7wh3dpd957nk86ldx7xu2jussvlqhrd
```

This address is derived from the default seed `quorum-culture-web-agent-phase1-seed-v1` and is stable across all restarts. Override it by setting a different `CULTURE_WEB_AGENT_SEED` (which produces a different stable address).

## Protocol

**Chat Protocol v0.3.0** (ASI:One discoverable)

This agent uses the standard uAgents Chat Protocol v0.3.0, making it directly reachable from ASI:One and the Agentverse chat UI.

### Input

Send a `ChatMessage` containing a market question as plain text. Example:

```
Will Dune: Part Two win Best Picture at the 2026 Oscars?
```

The agent also accepts a custom `EvidenceRequest` message (for orchestrator-to-agent calls from `orchestrator_agent.py`).

### Output

1. **Acknowledgement:** A `ChatAcknowledgement` sent immediately on receipt (ack-first; the web fetch runs after the ack with a hard timeout).
2. **Bundle reply:** A `ChatMessage` with a human-readable evidence summary **plus** a fenced ` ```json ` block containing the full `EvidenceChunkMsg` array.

Each chunk in the bundle has the following shape:

```json
{
  "source_type": "culture_web",
  "text": "=== Culture/Web Source: <title> ===\nURL: ...\nQuery: ...\n\n<rendered page text>",
  "source_url": "https://...",
  "confidence": 0.8,
  "metadata": {
    "kind": "news | odds",
    "fetched_via": "serper | browserbase",
    "source_strength": "web",
    "observed_at": "2026-06-20T00:00:00Z",
    "query": "<the search query used>",
    "title": "<page title>"
  }
}
```

The bundle always contains at least 2 chunks. If no web provider is configured / reachable it falls back to a tiny stub — so a reply is never empty.

### Example questions

- `Will Dune: Part Two win Best Picture at the 2026 Oscars?`
- `Will the new Marvel film gross over $100M opening weekend?`
- `Will Taylor Swift's album debut at #1 on the Billboard 200?`

## Required secrets

Set these as **Agentverse secrets** (or in the repo-root `.env` when running locally):

| Secret | Purpose |
| --- | --- |
| `SERPER_API_KEY` | Serper.dev Google search results (preferred provider) |
| `BROWSERBASE_API_KEY` | Browserbase DuckDuckGo search + page render fallback |
| `CULTURE_WEB_AGENT_SEED` | *(optional)* deterministic seed for a stable agent address |

At least one of `SERPER_API_KEY` / `BROWSERBASE_API_KEY` is needed for live evidence; with neither, the agent still runs and returns the stub bundle.

## Tags

The `innovationlab` and `hackathon` tags are applied via the shields.io badges at the top of this README — Agentverse derives an agent's marketplace tags from its README badges (not from a separate UI field).

## Run / deploy (mailbox)

```bash
# from the repo root
python uagents_deploy/culture_web_agent.py
# open the printed Agent Inspector link -> Connect -> Mailbox -> Finish
# (registers it on Agentverse + ASI:One; the seed-derived address stays stable)
```

Local round-trip check (two terminals):

```bash
python uagents_deploy/culture_web_agent.py     # terminal A
python uagents_deploy/send_test_culture.py     # terminal B -> GOT ACK + GOT BUNDLE REPLY
```

## Try it from ASI:One

1. Go to [https://asi1.ai](https://asi1.ai) and search for this agent by name (`culture_web_agent`) or address.
2. Send a question like: "Will Dune: Part Two win Best Picture at the 2026 Oscars?"
3. You receive an ack, then a readable evidence summary + the full JSON bundle.

## Architecture Notes

- **Dual-protocol:** Chat Protocol v0.3.0 (ASI:One / human chat) + a custom `EvidenceCollection` protocol (orchestrator machine-to-machine).
- **Self-contained:** no `app.services.*` imports — the entire web layer is inlined in `culture_evidence.py`, so it deploys equally well as a hosted Agentverse agent or a local mailbox agent.
- **Fixed seed / stable address:** the `agent1q…` address never changes while `CULTURE_WEB_AGENT_SEED` is unchanged.
- **Ack-first + timeout:** acknowledges immediately, then awaits the async web collection with a hard timeout so the handler never hangs.
- **Demo-safe:** live (Serper/Browserbase) → stub, so a reply is never empty even with no provider configured.