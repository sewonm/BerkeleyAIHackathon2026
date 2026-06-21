# Agent Chat Interface Testing Guide

## Overview

Both the **Compression Agent** and **Decision Agent** now have interactive chat interfaces that you can test via Agentverse!

You can:
- Type **'demo'** to see a full working example with sample data
- Send **JSON** to test with your own data
- Get **help** messages explaining how to use each agent

---

## Compression Agent Testing

### Starting the Agent

```bash
cd uagents_deploy
python standalone_compression_agent.py
```

**Expected output:**
```
[compression_agent] Compression Agent started!
[compression_agent] Address: agent1q...
[compression_agent] ASI:One chat protocol: ENABLED
```

### Testing via Agentverse Chat

1. **Copy the Agent Inspector URL** from terminal
2. **Open in browser** → Connect to Mailbox
3. **Go to Chat tab**

### Quick Demo Test

**Type in chat:**
```
demo
```

**Expected Response:**
```
Demo Compression Complete 🗜️

Input:
- Market: Will France win the World Cup 2026?
- Evidence chunks: 5
- Aggressiveness: 0.5

Compression Metrics:
- Raw tokens: 234
- Compressed tokens: 78
- Compression ratio: 3.0x
- Claims extracted: 5
- Consensus items: 3

Top YES Evidence (3 items):
• France won 4 of last 5 matches against top-ranked opponents
• Current betting odds favor France at 58% implied probability
• No major injuries reported in starting lineup

Top NO Evidence (1 items):
• France struggled in last friendly match

Contradictions Found: 1
⚠️ Strong recent form conflicts with weak friendly performance

Compressed Context Preview:
```
MARKET: Will France win the World Cup 2026?

TOP YES EVIDENCE:
• France won 4 of last 5 matches...
...
```

---

### Testing with Your Own Data

**Type in chat:**
```json
{
  "market_question": "Will Bitcoin reach $100k by end of 2026?",
  "evidence_chunks": [
    {
      "market_id": "btc-100k",
      "source_agent": "financial_agent",
      "source_type": "news",
      "text": "Bitcoin has shown strong momentum with institutional adoption increasing. Current price at $58k represents 72% gain needed to reach $100k target."
    },
    {
      "market_id": "btc-100k",
      "source_agent": "financial_agent",
      "source_type": "market",
      "text": "Kalshi market pricing YES at 65% for Bitcoin reaching $100k by 2026. Trading volume has doubled in the past month."
    },
    {
      "market_id": "btc-100k",
      "source_agent": "financial_agent",
      "source_type": "analysis",
      "text": "However, regulatory uncertainty remains a significant headwind. SEC actions against crypto exchanges could impact price momentum."
    }
  ],
  "current_yes_price": 0.65,
  "aggressiveness": 0.5
}
```

**Expected:** Compression analysis with your data showing:
- Token count reduction
- Extracted claims
- Top YES/NO evidence
- Contradictions detected
- Compressed context output

---

## Decision Agent Testing

### Starting the Agent

```bash
cd uagents_deploy
python standalone_decision_agent.py
```

**Expected output:**
```
[decision_agent] Decision Agent started!
[decision_agent] Address: agent1q...
[decision_agent] ASI:One chat protocol: ENABLED
```

### Testing via Agentverse Chat

1. **Copy the Agent Inspector URL** from terminal
2. **Open in browser** → Connect to Mailbox
3. **Go to Chat tab**

### Quick Demo Test

**Type in chat:**
```
demo
```

**Expected Response:**
```
Demo Decision Complete 🎯

Market Question: Will France win the World Cup 2026?

Input Data:
- Current YES price: $0.62 (62%)
- Current NO price: $0.38 (38%)
- Risk tolerance: moderate
- Max position: $100.00

---

TRADING DECISION: BUY_YES

Analysis:
- Fair Value Estimate: 68.5%
- Current Market Price: 62.0%
- Edge: +6.5% ✅ (favorable)
- Confidence: 71.2%

Position Sizing (Kelly Criterion):
- Suggested Position: $24.50
- Kelly Fraction: 24.50%
- Max Position: $100.00

Reasoning:
Based on the compressed evidence, France shows strong recent form with
4 wins in last 5 matches against top opponents. Betting markets slightly
undervalue their chances at 62% vs our fair value estimate of 68.5%.
Key players are healthy and team fundamentals are solid...

Key Evidence Used:
• France won 4 of last 5 matches against top-ranked opponents
• Current betting odds favor France at 58% implied probability
• All key players healthy and training
• Kalshi market pricing YES at $0.62

Risk Factors:
⚠️ Recent friendly match showed weak performance
⚠️ Historical World Cup volatility suggests upsets are common
⚠️ Limited information on opponent strength

Missing Information:
❓ Opponent team composition not finalized
❓ Weather conditions unknown
❓ Home/away advantage not specified

---

To test with your own data, send JSON:
{
  "market_question": "Your question",
  "current_yes_price": 0.62,
  "current_no_price": 0.38,
  "compressed_context": "Your compressed evidence...",
  "risk_tolerance": "moderate"
}
```

---

### Testing with Your Own Data

**Type in chat:**
```json
{
  "market_question": "Will Bitcoin reach $100k by end of 2026?",
  "resolution_criteria": "Resolves YES if Bitcoin trades at or above $100,000 USD at any point before December 31, 2026",
  "current_yes_price": 0.65,
  "current_no_price": 0.35,
  "compressed_context": "MARKET: Will Bitcoin reach $100k by end of 2026?\n\nTOP YES EVIDENCE:\n• Bitcoin showing strong institutional adoption, current price $58k needs 72% gain\n• Kalshi market pricing YES at 65%, trading volume doubled\n• Historical price trends suggest $100k achievable within timeframe\n\nTOP NO EVIDENCE:\n• Regulatory uncertainty remains significant headwind\n• SEC actions against exchanges could impact momentum\n\nCONSENSUS: Strong fundamentals but regulatory risk creates uncertainty",
  "max_position_size": 100.0,
  "risk_tolerance": "moderate"
}
```

**Expected:** Decision analysis with:
- Trading action (BUY_YES/BUY_NO/HOLD)
- Fair value estimate
- Edge calculation
- Kelly Criterion position sizing
- Detailed reasoning
- Risk factors
- Missing information

---

## Testing Both Agents Together (Manual Pipeline)

You can manually test the full pipeline by copying output from one agent to another:

### Step 1: Get Compressed Context

**In Compression Agent chat, type:**
```
demo
```

**Copy the "Compressed Context Preview" section**

### Step 2: Make Decision

**In Decision Agent chat, send JSON with the compressed context:**
```json
{
  "market_question": "Will France win the World Cup 2026?",
  "current_yes_price": 0.62,
  "current_no_price": 0.38,
  "compressed_context": "[PASTE COMPRESSED CONTEXT HERE]",
  "risk_tolerance": "moderate"
}
```

**Result:** Full pipeline test showing compression → decision flow!

---

## Input/Output Examples

### Compression Agent

#### Input (JSON):
```json
{
  "market_question": "Will Lakers beat Celtics?",
  "evidence_chunks": [
    {"market_id": "lakers-celtics", "source_agent": "sports", "source_type": "stats", "text": "Lakers won last 3 home games"},
    {"market_id": "lakers-celtics", "source_agent": "sports", "source_type": "odds", "text": "Betting odds favor Lakers at 55%"}
  ],
  "aggressiveness": 0.5
}
```

#### Output:
```
Compression Complete

Metrics:
- Raw tokens: 89
- Compressed tokens: 34
- Compression ratio: 2.62x
- Claims extracted: 2
- Consensus items: 2

Compressed Context:
```
MARKET: Will Lakers beat Celtics?

TOP YES EVIDENCE (55% confidence):
• Lakers won last 3 home games showing strong home court advantage
• Betting odds favor Lakers at 55% implied probability

CONSENSUS: Lakers slightly favored based on recent home performance
```

Top YES Evidence: 2 items
Top NO Evidence: 0 items
Contradictions Found: 0
```

---

### Decision Agent

#### Input (JSON):
```json
{
  "market_question": "Will Lakers beat Celtics?",
  "current_yes_price": 0.52,
  "current_no_price": 0.48,
  "compressed_context": "MARKET: Will Lakers beat Celtics?\n\nTOP YES EVIDENCE:\n• Lakers won last 3 home games\n• Betting odds favor Lakers at 55%",
  "risk_tolerance": "moderate"
}
```

#### Output:
```
Trading Decision for: Will Lakers beat Celtics?

Decision: BUY_YES

Fair Value Estimate: 58.00%
Current Market Price: 52.00%
Edge: +6.00%

Position Sizing:
- Suggested Position: $18.50
- Max Position: $100.00
- Confidence: 64.3%

Reasoning:
Based on recent home game performance and betting market consensus,
Lakers appear undervalued at current price of 52%. Fair value estimate
of 58% suggests 6% edge...

Risk Factors:
- Limited data on Celtics' away performance
- Sample size of only 3 games may not be statistically significant
- Injury status not factored into analysis
```

---

## Comparison Table

| Feature | Compression Agent | Decision Agent |
|---------|------------------|----------------|
| **Primary Function** | Compress evidence, extract claims | Make trading decisions |
| **Input** | Evidence chunks (text) | Compressed context + prices |
| **Output** | Compressed context | Trading action + position size |
| **Demo Mode** | ✅ Type 'demo' | ✅ Type 'demo' |
| **JSON Support** | ✅ Full support | ✅ Full support |
| **Help Command** | ✅ Auto-shown for invalid input | ✅ Auto-shown for invalid input |
| **ASI:One Compatible** | ✅ Yes | ✅ Yes |
| **Claude Integration** | ❌ Heuristic-based | ✅ Claude reasoning (if API key set) |

---

## Troubleshooting

### Problem: "Chat protocol not available"

**Error in terminal:**
```
[Warning] Chat protocol not available - ASI:One integration disabled
```

**Solution:**
```bash
pip install uagents[chat]
```

---

### Problem: Demo returns error

**Error:**
```
Error processing request: 'NoneType' object has no attribute...
```

**Solution:** Check that the agent started successfully. Look for:
```
[agent_name] Agent started!
[agent_name] ASI:One chat protocol: ENABLED
```

---

### Problem: JSON parsing error

**Error:**
```
Error: JSONDecodeError: Expecting property name...
```

**Solution:**
- Ensure JSON is valid (use jsonlint.com to validate)
- Check all quotes are double quotes `"` not single `'`
- Ensure no trailing commas

---

### Problem: Can't connect to agent

**Browser shows:** "Could not find this Agent on your local network"

**Solution:**
1. Ensure agent is running (check terminal)
2. Check browser allows localhost connections
3. Try refreshing the Agent Inspector page
4. Restart agent if needed

---

## Testing Checklist

### Compression Agent
- [ ] Agent starts without errors
- [ ] Chat protocol shows ENABLED in logs
- [ ] Connected to mailbox via Agentverse
- [ ] Type 'demo' → Get demo compression result
- [ ] Type 'help' → Get help message
- [ ] Send valid JSON → Get compression output
- [ ] Verify compression ratio > 1.0x
- [ ] Verify claims extracted count
- [ ] Check contradictions detection works

### Decision Agent
- [ ] Agent starts without errors
- [ ] Chat protocol shows ENABLED in logs
- [ ] Connected to mailbox via Agentverse
- [ ] Type 'demo' → Get demo decision result
- [ ] Type 'help' → Get help message
- [ ] Send valid JSON → Get decision output
- [ ] Verify trading action (BUY_YES/BUY_NO/HOLD)
- [ ] Check Kelly Criterion position sizing
- [ ] Verify edge calculation
- [ ] Check risk factors listed

---

## Next Steps

Once you've tested both agents individually:

1. **Deploy them to Agentverse** (keep them running)
2. **Get their agent addresses** from terminal output
3. **Set addresses in orchestrator**:
   ```bash
   export COMPRESSION_AGENT_ADDRESS="agent1q..."
   export DECISION_AGENT_ADDRESS="agent1q..."
   ```
4. **Start orchestrator** and test the full pipeline!

The orchestrator will automatically:
- Collect evidence from sports/financial agents
- Send to compression agent
- Send compressed context to decision agent
- Show you the decision and ask for confirmation
- Execute trade on Kalshi if you confirm

---

**Ready to test!** 🚀

Start with the **demo** command in each agent to see them in action!
