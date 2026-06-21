# Quorum Sports Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:sports](https://img.shields.io/badge/sports-32CD32)

Given a Kalshi **sports** market question, this agent resolves the sport/league and the live (or most-recent) game, then returns a wide **raw evidence bundle** as `EvidenceChunk`s — ready for a downstream compression engine.

**Sport-agnostic** (NBA/NFL/MLB/soccer/…) via a sport→source registry; showcased on the **2026 FIFA World Cup** and **MLB**. Each evidence bundle blends:

- **Live ESPN HTTP anchor** — score/state, box/match stats, event log, betting **odds with open/close/current line movement**, win/implied probability, injuries, lineups.
- **Browserbase noisy layer** — raw scraped text from deep-stats + match-thread sources (FBref/Sofascore/Reddit).

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

1. **Acknowledgement:** A `ChatAcknowledgement` sent immediately on receipt (ack-first; the blocking fetch runs off the event loop).
2. **Bundle reply:** A `ChatMessage` with a human-readable evidence summary **plus** a fenced ` ```json ` block containing the full `EvidenceChunkMsg` array.

Each chunk in the bundle has the following shape:

```json
{
  "source_type": "sports_video",
  "text": "<raw evidence text>",
  "source_url": "https://site.api.espn.com/...",
  "confidence": 0.9,
  "metadata": {
    "kind": "score_state | box_stats | event_log | odds | win_probability | injuries | lineups | deep_stats | match_thread",
    "fetched_via": "http | browserbase",
    "source_strength": "anchor | noisy",
    "observed_at": "2026-06-20T00:00:00Z",
    "sport": "soccer",
    "league": "fifa.world",
    "event_id": "760447"
  }
}
```

The bundle always contains at least 2 chunks. If live data is unavailable it falls back to recorded fixtures, then to a tiny stub — so a reply is never empty.

### Example questions

- `Will Argentina win the 2026 FIFA World Cup?`  → soccer/fifa.world
- `Will the Yankees win this MLB game?`          → baseball/mlb
- `Will the Lakers cover the spread tonight?`     → basketball/nba (config-only)

## Run / deploy (mailbox)

```bash
# from the repo root
python uagents_deploy/sports_video_agent.py
# open the printed Agent Inspector link -> Connect -> Mailbox -> Finish
# (registers it on Agentverse + ASI:One; the address above stays stable)
```

Local round-trip check (two terminals):

```bash
python uagents_deploy/sports_video_agent.py      # terminal A
python uagents_deploy/send_test_chat.py          # terminal B -> GOT ACK + GOT BUNDLE REPLY
```

## Try it from ASI:One

1. Go to [https://asi1.ai](https://asi1.ai) and search for this agent by name (`sports_video_agent`) or address.
2. Send a question like: "Will Argentina beat Brazil in the World Cup?"
3. You receive an ack, then a readable evidence summary + the full JSON bundle.

## Architecture Notes

- **Dual-protocol:** Chat Protocol v0.3.0 (ASI:One / human chat) + a custom `SportsVideoEvidence` protocol (orchestrator machine-to-machine).
- **Fixed seed / stable address:** the `agent1q…` address above never changes while the seed constant is unchanged (SA-AGENT-01).
- **Mailbox agent:** runs locally with `mailbox=True` + `publish_agent_details=True`; deploy via the Agent Inspector (Connect → Mailbox). Because it runs locally it imports the project's live collectors (`app.services.*`) for real data.
- **Ack-first + non-blocking:** acknowledges immediately, then runs the blocking HTTP/scrape off the event loop via `asyncio.to_thread` with a timeout (SA-INT-01/02).
- **Demo-safe:** live → recorded fixtures → stub, so a reply is never empty even with the network off.
