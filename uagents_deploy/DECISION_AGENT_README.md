# Quorum Decision Agent

![tag:innovationlab](https://img.shields.io/badge/tag-innovationlab-blue) ![tag:hackathon](https://img.shields.io/badge/tag-hackathon-green) ![domain:prediction_markets](https://img.shields.io/badge/domain-prediction__markets-orange)

Given compressed market context from upstream compression engines, this agent makes quantitative trading decisions using Claude-powered reasoning combined with Kelly Criterion position sizing — outputting actionable BUY/SELL/HOLD recommendations with confidence levels and risk analysis.

Market-agnostic (works with sports, finance, politics, culture markets). Each trading decision includes:

- **Fair value estimation** — Calculates true probability using Claude analysis of compressed evidence
- **Edge calculation** — Compares fair value vs current market price to identify mispricing
- **Kelly Criterion sizing** — Determines optimal position size based on edge and confidence
- **Risk adjustment** — Applies conservative/moderate/aggressive multipliers based on risk tolerance
- **Reasoning transparency** — Provides detailed explanation of decision logic
- **Evidence ranking** — Identifies key supporting evidence for the decision
- **Risk factor analysis** — Flags potential downsides and uncertainties
- **Missing information detection** — Highlights gaps that could improve decision quality

## Agent Address

```
<deploy to get address>
```

This address is derived from the fixed seed `decision_agent_standalone_seed_change_in_production` and is stable across all restarts.

## Tags

The `innovationlab` and `hackathon` tags are applied via the shields.io badges at the top of this README — Agentverse derives an agent's marketplace tags from its README badges (not from a separate UI field).

## Protocol

### Chat Protocol v0.3.0 (ASI:One discoverable)

This agent uses the standard uAgents Chat Protocol v0.3.0, making it directly reachable from ASI:One and the Agentverse chat UI.

### Custom Protocol: StandaloneTradingDecision

For orchestrator-to-agent machine-to-machine communication.

## Input

### Via Chat (ASI:One / Agentverse UI)

**Demo mode** — Type one of:
```
@decision-agent demo
@decision-agent test
@decision-agent example
```

**JSON mode** — Send a JSON request:
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "resolution_criteria": "Resolves YES if France wins the 2026 FIFA World Cup",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "compressed_context": "MARKET: Will France win the World Cup 2026?\n\nTOP YES EVIDENCE (62% confidence):\n• France defeated Brazil 2-1 in their most recent match with goals from Mbappe\n• Betting markets favor France at 52% win probability vs Brazil's 31%\n• Key French players Mbappe and Griezmann are healthy and in good form\n\nTOP NO EVIDENCE (38% confidence):\n• N'Golo Kante is questionable with an ankle injury\n• Brazil's Casemiro is suspended, but this may favor France\n\nCONSENSUS: France shows strong recent form and favorable odds, but injury concerns for Kante create some uncertainty. Evidence suggests France is the favorite but not a certainty.",
  "max_position_size": 100.0,
  "risk_tolerance": "moderate"
}
```

**Required fields:**
- `market_question` (string) — The prediction market question
- `current_yes_price` (float, 0.0-1.0) — Current YES market price
- `current_no_price` (float, 0.0-1.0) — Current NO market price
- `compressed_context` (string) — **Compressed evidence from compression agent**

**Optional fields:**
- `resolution_criteria` (string) — How the market resolves
- `max_position_size` (float) — Maximum dollars to risk (default: 100.0)
- `risk_tolerance` (string) — "conservative" | "moderate" | "aggressive" (default: "moderate")

### Via Custom Protocol (Orchestrator)

The agent accepts `TradingDecisionRequest` messages with the same structure as the JSON input above.

## Output

### Acknowledgement
A `ChatAcknowledgement` sent immediately on receipt (ack-first pattern).

### Trading Decision

**Via Chat:** A `ChatMessage` with formatted decision results.

**Example output:**
```
Demo Decision Complete 🎯

Market Question: Will France win the World Cup 2026?

Input Data:
- Current YES price: $0.52 (52%)
- Current NO price: $0.48 (48%)
- Risk tolerance: moderate
- Max position: $100.00

---

TRADING DECISION: BUY_YES

Analysis:
- Fair Value Estimate: 58.5%
- Current Market Price: 52.0%
- Edge: +6.5% ✅ (favorable)
- Confidence: 71.2%

Position Sizing (Kelly Criterion):
- Suggested Position: $24.50
- Kelly Fraction: 24.50%
- Max Position: $100.00

Reasoning:
Based on recent match performance against Brazil and betting market analysis, France appears undervalued at the current price of 52%. The fair value estimate of 58.5% suggests a meaningful 6.5% edge. Key French players are healthy and the team has demonstrated strong form. The injury concern for N'Golo Kante adds some uncertainty, but the overall evidence supports taking a YES position. Kelly Criterion suggests allocating 24.5% of maximum position size.

Key Evidence Used:
• France defeated Brazil 2-1 in their most recent high-stakes match
• Betting markets show 52% win probability with positive line movement
• Key offensive players Mbappe and Griezmann are healthy and performing well
• Recent form shows 4 wins in last 5 matches against top opponents
• No major injury concerns for starting lineup (except Kante questionable)

Risk Factors:
⚠️ N'Golo Kante is questionable with an ankle injury, affecting defensive stability
⚠️ Limited information on specific tournament stage and opponent
⚠️ World Cup outcomes are historically volatile with upset potential
⚠️ Sample size of recent matches may not fully represent tournament performance
⚠️ Home/away advantage and weather conditions not factored in

Missing Information:
❓ Opponent in the World Cup final is not specified
❓ Tournament stage (group/knockout/final) is unclear
❓ Recent head-to-head record against likely opponents not provided

---

To test with your own data, send JSON:
{
  "market_question": "Your question",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "compressed_context": "Your compressed evidence...",
  "risk_tolerance": "moderate"
}
```

### Via Custom Protocol

Returns `TradingDecisionResponse` containing:

```python
{
  "request_id": "uuid",
  "market_id": "france-wc-2026",
  "market_question": "Will France win the World Cup 2026?",
  "recommendation": "BUY_YES",  # or "BUY_NO" or "HOLD"
  "action": "BUY_YES",
  "side": "yes",  # or "no"
  "estimated_fair_value": 0.585,
  "current_market_price": 0.52,
  "edge": 0.065,  # 6.5% edge
  "confidence": 0.712,
  "kelly_fraction": 0.245,
  "suggested_position_size": 24.50,
  "max_position_size": 100.0,
  "reasoning": "Based on recent match performance against Brazil and betting market analysis, France appears undervalued at current price of 52%. Fair value estimate of 58.5% suggests 6.5% edge. Injury concern for Kante adds uncertainty but overall evidence supports YES position.",
  "key_evidence": [
    "France defeated Brazil 2-1 in most recent match",
    "Betting markets show 52% win probability",
    "Key offensive players healthy and performing well",
    "Strong recent form with 4 wins in last 5 matches"
  ],
  "risk_factors": [
    "N'Golo Kante questionable with ankle injury",
    "Tournament stage not specified",
    "World Cup outcomes historically volatile",
    "Limited head-to-head data"
  ],
  "missing_info": [
    "Opponent in final not specified",
    "Tournament stage unclear",
    "Recent head-to-head record not provided"
  ],
  "fair_probability": 0.585
}
```

## Decision Logic

### Action Determination

- **BUY_YES** — Fair value > current YES price + minimum edge threshold
- **BUY_NO** — Fair value < current NO price - minimum edge threshold
- **HOLD** — Edge is insufficient or confidence is too low

### Kelly Criterion Position Sizing

```
Kelly % = (Edge × Confidence) / Edge
Position = Kelly % × Risk Multiplier × Max Position

Risk Multipliers:
- Conservative: 0.25× (quarter Kelly)
- Moderate: 0.50× (half Kelly)
- Aggressive: 1.00× (full Kelly)
```

### Edge Calculation

```
Edge = |Fair Value - Current Price|
```

Minimum edge threshold: 2% (configurable)

### Confidence Levels

- High (>75%): Strong evidence, clear consensus
- Medium (50-75%): Good evidence, some uncertainty
- Low (<50%): Weak evidence, high uncertainty

## Example Decisions

**High-confidence BUY:**
```
Fair Value: 68% | Market Price: 52% | Edge: 16%
→ BUY_YES, Position: $48 (moderate risk)
```

**Marginal HOLD:**
```
Fair Value: 53% | Market Price: 52% | Edge: 1%
→ HOLD (edge below 2% threshold)
```

**High-confidence SELL:**
```
Fair Value: 35% | Market Price: 48% | Edge: 13%
→ BUY_NO (sell YES), Position: $32 (moderate risk)
```

## Run / Deploy (Mailbox)

```bash
# from the repo root
python uagents_deploy/standalone_decision_agent.py

# open the printed Agent Inspector link -> Connect -> Mailbox -> Finish
# (registers it on Agentverse + ASI:One; the address stays stable)
```

## Try it from ASI:One

1. Go to https://asi1.ai and search for this agent by name (`decision_agent_standalone`) or address
2. Send a test command: `@decision-agent demo`
3. You receive an ack, then a formatted trading decision with reasoning

## Architecture Notes

- **Dual-protocol**: Chat Protocol v0.3.0 (ASI:One / human chat) + custom `StandaloneTradingDecision` protocol (orchestrator machine-to-machine)
- **Fixed seed / stable address**: The agent address never changes while the seed constant is unchanged
- **Mailbox agent**: Runs locally with `mailbox=True`; deploy via Agent Inspector (Connect → Mailbox)
- **Ack-first**: Acknowledges immediately, then processes decision
- **Claude-powered reasoning**: Uses Claude to analyze compressed evidence and estimate fair value (if `ANTHROPIC_API_KEY` is set)
- **Kelly Criterion**: Mathematically optimal position sizing based on edge and probability
- **Risk-adjusted**: Applies conservative/moderate/aggressive multipliers
- **@mention aware**: Strips `@decision-agent` prefix from chat messages for ASI:One compatibility

## Decision Pipeline

1. **Evidence Analysis** — Claude processes compressed context to understand market dynamics
2. **Fair Value Estimation** — Estimates true probability of YES outcome
3. **Edge Calculation** — Compares fair value vs current market price
4. **Confidence Assessment** — Evaluates strength of evidence and consensus
5. **Action Determination** — Decides BUY_YES / BUY_NO / HOLD based on edge threshold
6. **Position Sizing** — Applies Kelly Criterion with risk multiplier
7. **Risk Analysis** — Identifies potential downsides and missing information
8. **Reasoning Synthesis** — Generates transparent explanation of decision logic

## Integration

**Upstream:** Receives compressed context from compression_agent_standalone

**Downstream:** Sends trading decision to kalshi_agent or orchestrator for user confirmation

**Orchestrator:** Called by orchestrator_agent.py as part of the full prediction market analysis pipeline

## Configuration

- `ANTHROPIC_API_KEY` (required) — For Claude-powered reasoning and fair value estimation
- Port: 8003 (configurable via `AGENT_PORT`)
- Seed: Set via `AGENT_SEED` environment variable for production
- Default risk tolerance: "moderate" (0.5× Kelly multiplier)
- Minimum edge threshold: 2%
- Default max position size: $100

## Error Handling

- **Missing Claude API key**: Falls back to heuristic fair value estimation
- **Invalid compressed context**: Returns HOLD with low confidence
- **Price inconsistency**: Validates YES + NO prices sum to ~1.0
- **Extreme edge**: Caps position size at maximum even with large edge

---

**Last Updated:** 2026-06-20
**Status:** ✅ Production Ready
**Agent Type:** Mailbox Agent (Local deployment with Agentverse registration)
