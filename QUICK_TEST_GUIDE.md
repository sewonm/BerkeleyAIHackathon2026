# Quick Test Guide - Natural Language Orchestrator

## Prerequisites

Before testing, ensure you have deployed these agents and have their addresses:

### ✅ Already Deployed (Your Friend's Agents)
- **Sports Video Agent**: `agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g`
- **Financial Research Agent**: `agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7`

### ⏳ Need to Deploy
- **Compression Agent**: Deploy `uagents_deploy/standalone_compression_agent.py`
- **Decision Agent**: Deploy `uagents_deploy/standalone_decision_agent.py`
- **Kalshi Agent**: Deploy `uagents_deploy/standalone_kalshi_agent.py`

---

## Quick Start (30 seconds)

### 1. Set Agent Addresses (One-Time Setup)

```bash
# Already deployed agents
export SPORTS_VIDEO_AGENT_ADDRESS="agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g"
export FINANCIAL_RESEARCH_AGENT_ADDRESS="agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7"

# You need to deploy these and get their addresses
export COMPRESSION_AGENT_ADDRESS="<your_compression_agent_address>"
export DECISION_AGENT_ADDRESS="<your_decision_agent_address>"
export KALSHI_AGENT_ADDRESS="<your_kalshi_agent_address>"
```

### 2. Start Orchestrator

```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./start_orchestrator.sh
```

**Expected output:**
```
=== Configuring Agent Addresses ===

✓ Financial Research Agent: agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7
✓ Sports Video Agent: agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g
⚠ Compression Agent: NOT SET (pipeline will stall without this)
⚠ Decision Agent: NOT SET (pipeline will stall without this)
⚠ Kalshi Agent: NOT SET (trade execution disabled)

=== Starting Orchestrator Agent ===

[orchestrator_agent] Orchestrator Agent started!
[orchestrator_agent] Address: agent1q...
[orchestrator_agent] ASI:One chat protocol: ENABLED (DeltaV compatible)
```

### 3. Connect to Mailbox

1. **Copy the Agent Inspector URL** from the terminal output
2. **Open it in your browser**
3. **Click "Connect" → "Mailbox" → "Finish"**
4. **Go to the "Chat" tab**

---

## Test Scenarios

### Test 1: Sports Question (Basic Flow)

**Type in chat:**
```
Will France win the World Cup 2026?
```

**Expected Response 1 (Immediate):**
```
🔍 Analyzing your question

Question: Will France win the World Cup 2026?
Category: sports

Gathering evidence from specialized agents...
```

**Expected Response 2 (10-30 seconds):**
```
📊 Trading Decision Analysis Complete

Question: Will France win the World Cup 2026?

Recommendation: YES
Confidence: 68.5%
Fair Probability: 62.3%

Reasoning:
[Analysis based on ESPN data, odds, etc.]

Key Supporting Evidence:
• France won 4 of last 5 matches...
• Current betting odds favor France...
• No major injuries reported...

---

⚠️ Do you want to execute this trade on Kalshi?

Reply 'yes' to execute the trade or 'no' to cancel.
```

**Test Confirmation - Type:**
```
yes
```

**Expected Response:**
```
✅ Trade execution initiated

Sending YES trade to Kalshi agent...

You will receive confirmation once the trade is executed.
```

---

### Test 2: Financial Question

**Type:**
```
Will Bitcoin reach $100k by end of 2026?
```

**Expected:**
- Category detected: **financial**
- Evidence from: **financial_research_agent**
- Decision recommendation with reasoning
- Confirmation prompt

**Test Cancellation - Type:**
```
no
```

**Expected Response:**
```
❌ Trade cancelled

No trade will be executed. Analysis results have been saved for your reference.
```

---

### Test 3: Help Command

**Type:**
```
help
```

**Expected Response:**
```
**Orchestrator Agent - Prediction Market Analysis**

I analyze prediction markets and help you make informed trading decisions!

**How to use me**:

Just ask me a natural language question about any prediction market:

**Sports examples:**
- "Will France win the World Cup 2026?"
- "Will Lakers beat the Celtics?"
...
```

---

### Test 4: Multiple Questions

**First question:**
```
Will Lakers beat Celtics?
```

**Wait for decision** → Reply `no` to cancel

**Second question:**
```
Will S&P 500 close above 5000?
```

**Wait for decision** → Reply `yes` to execute

**Expected:** Each question handled independently, confirmations don't interfere

---

## Troubleshooting

### Problem: "Compression agent address not configured"

**Log shows:**
```
[orchestrator_agent] Compression agent address not configured
```

**Solution:**
1. Deploy `standalone_compression_agent.py`
2. Get its agent address from the terminal output
3. Set `export COMPRESSION_AGENT_ADDRESS="<address>"`
4. Restart orchestrator

---

### Problem: "Decision agent address not configured"

**Log shows:**
```
[orchestrator_agent] Decision agent address not configured
```

**Solution:**
1. Deploy `standalone_decision_agent.py`
2. Get its agent address
3. Set `export DECISION_AGENT_ADDRESS="<address>"`
4. Restart orchestrator

---

### Problem: "Kalshi agent not configured"

**Response shows:**
```
❌ Kalshi agent not configured

Cannot execute trade - KALSHI_AGENT_ADDRESS not set.
```

**Solution:**
1. Deploy `standalone_kalshi_agent.py`
2. Get its agent address
3. Set `export KALSHI_AGENT_ADDRESS="<address>"`
4. Restart orchestrator

**Note:** You can still test the decision flow without Kalshi agent - you just won't be able to execute trades.

---

### Problem: Chat protocol not available

**Log shows:**
```
[Warning] Chat protocol not available - ASI:One integration disabled
Install with: pip install uagents[chat]
```

**Solution:**
```bash
pip install uagents[chat]
```

---

### Problem: Port 8000 already in use

**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Solution:**
```bash
# Kill existing orchestrator
lsof -ti:8000 | xargs kill -9

# Restart
./start_orchestrator.sh
```

---

### Problem: Agent not found on local network

**Browser shows:** "Could not find this Agent on your local network"

**Solution:**
1. Check browser settings - allow connection to localhost
2. Ensure orchestrator is running (check terminal)
3. Try refreshing the Agent Inspector page

---

## Verification Checklist

Before testing, verify:

- [ ] Orchestrator running without errors
- [ ] Log shows "ASI:One chat protocol: ENABLED"
- [ ] Sports agent address configured (✓ already set)
- [ ] Financial agent address configured (✓ already set)
- [ ] Compression agent deployed and address set
- [ ] Decision agent deployed and address set
- [ ] Kalshi agent deployed and address set (for trade execution)
- [ ] Connected to mailbox via Agent Inspector
- [ ] Chat tab is accessible

---

## Expected Timeline

### Without Compression/Decision Agents
- **User asks question** → Immediate ACK + processing notification
- **Evidence collection** → 5-10 seconds
- **Pipeline stalls** → No compression/decision response

### With All Agents Deployed
- **User asks question** → Immediate ACK + processing notification
- **Evidence collection** → 5-10 seconds
- **Compression** → 2-5 seconds
- **Decision analysis** → 3-8 seconds
- **Confirmation prompt** → Total ~10-30 seconds
- **User confirms** → Immediate
- **Trade execution** → 2-5 seconds
- **Total end-to-end** → ~15-40 seconds

---

## Sample Questions for Testing

### Sports (Auto-detected)
```
Will France win the World Cup 2026?
Will Lakers beat Celtics?
Will Argentina beat Brazil in the next World Cup qualifier?
Will Chiefs win the Super Bowl?
Will Dodgers make the playoffs?
```

### Financial (Auto-detected)
```
Will Bitcoin reach $100k by end of 2026?
Will S&P 500 close above 5000?
Will Ethereum reach $10k?
Will the stock market crash in 2026?
Will crypto regulation pass this year?
```

### Edge Cases (Test category detection)
```
Will Taylor Swift's new album go platinum?  # → culture
Will the election be decided by November?   # → culture
Will NASA launch the Mars mission in 2026?  # → culture
```

---

## Success Indicators

### ✅ Working Correctly

1. **Natural language accepted** - No JSON required
2. **Category auto-detected** - Sports/Financial correctly identified
3. **Evidence collected** - Sports or financial agent responds
4. **Decision generated** - YES/NO/HOLD with confidence
5. **Confirmation prompt sent** - Clear yes/no question
6. **User response handled** - Yes executes, No cancels
7. **Clean session end** - No hanging state

### ❌ Something Wrong

1. **"Unrecognized schema digest" error** - Chat protocol not working
2. **Pipeline stalls after evidence** - Compression agent missing
3. **No decision received** - Decision agent missing
4. **Trade execution fails** - Kalshi agent missing or misconfigured
5. **Multiple confirmations overlap** - State management bug

---

## Next Steps After Testing

1. **If it works** → Deploy to Agentverse permanently
2. **If compression/decision missing** → Deploy those agents first
3. **If Kalshi missing** → Deploy Kalshi agent for trade execution
4. **If category detection wrong** → Adjust keywords in `detect_category()`
5. **If everything works** → Start testing with real Kalshi markets!

---

**Quick Reference:**

| Agent | Address | Status |
|-------|---------|--------|
| Sports Video | `agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g` | ✅ Deployed |
| Financial Research | `agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7` | ✅ Deployed |
| Compression | `<deploy standalone_compression_agent.py>` | ⏳ Need to deploy |
| Decision | `<deploy standalone_decision_agent.py>` | ⏳ Need to deploy |
| Kalshi | `<deploy standalone_kalshi_agent.py>` | ⏳ Need to deploy |

---

**Ready to test!** 🚀
