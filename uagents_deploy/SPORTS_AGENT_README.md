# Quorum Sports Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:sports](https://img.shields.io/badge/sports-32CD32)

Gathers wide raw sports evidence for a Kalshi market and returns it as an EvidenceChunk bundle (Phase 1: stub bundle).

## Agent Address

```
agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g
```

This address is derived from the fixed seed `quorum-sports-agent-phase1-seed-v1` and is stable across all restarts.

## Tags

The `innovationlab` and `hackathon` tags are applied via the shields.io badges at the top of this README — Agentverse derives an agent's marketplace tags from its README badges (not from a separate UI field).

## Protocol

**Chat Protocol v0.3.0** (ASI:One discoverable)

This agent uses the standard uAgents Chat Protocol v0.3.0, making it directly reachable from ASI:One and the Agentverse chat UI.

### Input

Send a `ChatMessage` containing a market question as plain text. Example:

```
Will Argentina beat Brazil in the 2026 World Cup?
```

The agent also accepts a custom `EvidenceRequest` message (for orchestrator-to-agent calls from `orchestrator_agent.py`).

### Output

1. **Acknowledgement:** A `ChatAcknowledgement` sent immediately on receipt.
2. **Bundle reply:** A `ChatMessage` whose text is a JSON array of `EvidenceChunkMsg` objects.

Each chunk in the bundle has the following shape:

```json
{
  "source_type": "sports_video",
  "text": "<evidence text>",
  "source_url": "stub://sports/phase1",
  "confidence": 0.5,
  "metadata": {
    "kind": "scoreline | injury | ...",
    "fetched_via": "stub",
    "source_strength": "stub",
    "observed_at": "2026-06-21T00:00:00Z"
  }
}
```

The bundle always contains at least 2 chunks.

## Try it from ASI:One

1. Go to [https://asi1.ai](https://asi1.ai) and search for this agent by name (`sports_video_agent`) or address.
2. Start a conversation and send a question like: "Will Argentina beat Brazil in the World Cup?"
3. You will receive an ack, followed by a JSON bundle of `EvidenceChunkMsg` entries.

## Architecture Notes

- **Dual-protocol:** exposes both Chat Protocol v0.3.0 (for ASI:One / human chat) and a custom `SportsVideoEvidence` protocol (for `orchestrator_agent.py` machine-to-machine calls).
- **Fixed seed / stable address:** the `agent1q…` address above never changes as long as the seed constant is unchanged (SA-AGENT-01).
- **Mailbox agent:** runs with `mailbox=True` and `publish_agent_details=True`; deploy by running it and connecting via the Agent Inspector link (Connect → Mailbox), which registers it on Agentverse for asynchronous reachability + discovery.
- **Self-contained:** uses only `uagents`, `uagents_core`, stdlib, and `protocols.messages` — no internal app-package imports, so it runs anywhere.

## Phase 1 Stub Notice

Phase 1 returns canned stub evidence; live ESPN + Browserbase data land in later phases.

The stub bundle is returned deterministically regardless of the market question. The schema (including all four metadata keys) is final — later phases replace only the data-fetching internals.
