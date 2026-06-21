# Natural Language Orchestrator - Complete Implementation

## Overview

The orchestrator agent now accepts **natural language questions** via Agentverse chat and provides **interactive trade confirmation** before executing any trades on Kalshi.

## New User Flow

### 1. Ask a Natural Language Question

**User types:**
```
Will France win the World Cup 2026?
```

**Orchestrator responds:**
```
🔍 Analyzing your question

Question: Will France win the World Cup 2026?
Category: sports

Gathering evidence from specialized agents...
```

### 2. Evidence Collection (Automatic)

- **Auto-detects category** (sports/financial/culture) based on keywords
- **Routes to appropriate agents**:
  - Sports questions → sports_video_agent (ESPN stats, odds, injuries)
  - Financial questions → financial_research_agent (Kalshi data, prices)
  - Culture questions → culture_web_agent (if configured)
- **All agents respond** with EvidenceChunks

### 3. Compression & Decision (Automatic)

- Evidence sent to compression_agent
- Compressed context sent to decision_agent
- Decision agent analyzes and returns YES/NO/HOLD recommendation

### 4. Interactive Confirmation Prompt

**Orchestrator sends:**
```
📊 Trading Decision Analysis Complete

Question: Will France win the World Cup 2026?

Recommendation: YES
Confidence: 68.5%
Fair Probability: 62.3%

Reasoning:
Based on live sports data, France shows strong form with recent victories
against top-ranked opponents. Their key players are healthy and the team
has demonstrated consistent performance in qualifiers.

Key Supporting Evidence:
• France won 4 of last 5 matches against ranked opponents
• Current betting odds favor France at 58% implied probability
• No major injuries reported in starting lineup
• Strong defensive record in recent tournaments
• FIFA ranking: #3 globally

Missing Information:
• Opponent team composition not yet finalized
• Weather conditions for match date unknown
• Home/away advantage not specified

Analysis Metrics:
• Agents used: sports_video_agent, financial_research_agent
• Processing time: 12.3s
• Evidence compressed: 2.8x ratio

---

⚠️ Do you want to execute this trade on Kalshi?

Reply 'yes' to execute the trade or 'no' to cancel.

(This confirmation will expire in 5 minutes)
```

### 5. User Confirms or Cancels

#### Option A: User Confirms

**User types:**
```
yes
```

**Orchestrator sends to Kalshi agent and responds:**
```
✅ Trade execution initiated

Sending YES trade to Kalshi agent...

You will receive confirmation once the trade is executed.
```

The Kalshi agent then executes the trade and sends back execution results.

#### Option B: User Cancels

**User types:**
```
no
```

**Orchestrator responds:**
```
❌ Trade cancelled

No trade will be executed. Analysis results have been saved for your reference.
```

## Supported Input Formats

### Natural Language (Preferred)

Just ask a question:
- "Will France win the World Cup 2026?"
- "Will Bitcoin reach $100k by end of 2026?"
- "Will Lakers beat the Celtics?"
- "Will S&P 500 close above 5000?"

### Confirmation Responses

When prompted to confirm a trade:
- **YES**: `yes`, `y`, `confirm`, `execute`
- **NO**: `no`, `n`, `cancel`, `abort`

### Help

Get usage instructions:
- `help`
- `?`
- `how`
- `what`

## Category Auto-Detection

The orchestrator automatically detects the market category based on keywords:

### Sports Keywords
- Teams: Lakers, Celtics, Chiefs, Patriots, Yankees, Dodgers
- Sports: NBA, NFL, MLB, NHL, FIFA, World Cup, Olympics, Super Bowl
- Actions: win, beat, defeat, champion, game, match, score

### Financial Keywords
- Crypto: Bitcoin, BTC, ETH, Ethereum, crypto
- Markets: stock, S&P 500, NASDAQ, Dow
- General: price, dollar, USD, market, trading

### Default
If no sports or financial keywords detected, defaults to "culture" category.

## Required Agent Addresses

Configure these environment variables before starting the orchestrator:

### Evidence Collection Agents
```bash
export SPORTS_VIDEO_AGENT_ADDRESS="agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g"
export FINANCIAL_RESEARCH_AGENT_ADDRESS="agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7"
```

### Processing Agents (REQUIRED for pipeline)
```bash
export COMPRESSION_AGENT_ADDRESS="<deploy standalone_compression_agent.py>"
export DECISION_AGENT_ADDRESS="<deploy standalone_decision_agent.py>"
```

### Trade Execution Agent (REQUIRED for trading)
```bash
export KALSHI_AGENT_ADDRESS="<deploy standalone_kalshi_agent.py>"
```

### Optional Agents
```bash
export CULTURE_WEB_AGENT_ADDRESS="<optional - for culture/politics questions>"
```

## Starting the Orchestrator

### Quick Start (Recommended)
```bash
./start_orchestrator.sh
```

This script:
1. Kills any existing orchestrator on port 8000
2. Displays configured agent addresses
3. Starts the orchestrator with all environment variables set

### Manual Start
```bash
cd uagents_deploy
python orchestrator_agent.py
```

**Look for this in the logs:**
```
[orchestrator_agent] Orchestrator Agent started!
[orchestrator_agent] Address: agent1q...
[orchestrator_agent] Ready to orchestrate market analysis pipelines
[orchestrator_agent] Custom protocol: ENABLED (agent-to-agent communication)
[orchestrator_agent] ASI:One chat protocol: ENABLED (DeltaV compatible)
```

## Testing via Agentverse Chat

1. **Start the orchestrator** (see above)
2. **Open Agentverse Inspector** (link printed in terminal)
3. **Click "Connect" → "Mailbox" → "Finish"**
4. **Go to the Chat tab**
5. **Type a natural language question**:
   ```
   Will France win the World Cup 2026?
   ```
6. **Wait for decision** (typically 10-30 seconds)
7. **Confirm or cancel the trade** when prompted

## Example Complete Flow

```
[User] Will Bitcoin reach $100k by end of 2026?

[Orchestrator] 🔍 Analyzing your question
Question: Will Bitcoin reach $100k by end of 2026?
Category: financial
Gathering evidence from specialized agents...

[10-30 seconds pass]

[Orchestrator] 📊 Trading Decision Analysis Complete

Question: Will Bitcoin reach $100k by end of 2026?

Recommendation: YES
Confidence: 71.2%
Fair Probability: 65.8%

Reasoning:
Based on current market data, historical price trends, and adoption metrics,
Bitcoin shows strong momentum toward the $100k target. Current trading
volume and institutional interest support continued growth.

Key Supporting Evidence:
• Current price: $58,234 (up 12% this month)
• Historical volatility suggests $100k is achievable within timeframe
• Kalshi market pricing YES at 62% (slight undervalue)
• Institutional holdings increased 23% this quarter
• Regulatory clarity improving in major markets

Missing Information:
• Potential regulatory changes not yet announced
• Macroeconomic conditions for 2026 uncertain

Analysis Metrics:
• Agents used: financial_research_agent
• Processing time: 8.7s
• Evidence compressed: 3.2x ratio

---

⚠️ Do you want to execute this trade on Kalshi?

Reply 'yes' to execute the trade or 'no' to cancel.

(This confirmation will expire in 5 minutes)

[User] yes

[Orchestrator] ✅ Trade execution initiated

Sending YES trade to Kalshi agent...

You will receive confirmation once the trade is executed.

[Kalshi Agent] ✅ Trade executed successfully!

Market: Will Bitcoin reach $100k by end of 2026?
Side: YES
Quantity: 1 contract
Fill Price: $0.62
Total Cost: $62.00
Order ID: ord_abc123xyz
```

## Technical Implementation Details

### State Management

**Analysis State** (`analysis_state` dict):
- Tracks active pipeline executions
- Keyed by `request_id`
- Contains: market_request, evidence_responses, compression_response, decision_response, agents_used, timestamps

**Pending Confirmations** (`pending_confirmations` dict):
- Tracks trades awaiting user confirmation
- Keyed by `sender_address`
- Contains: decision_response, market_request, compression_response, agents_used, processing_time, timestamp
- Expires after 5 minutes (not yet implemented - TODO)

### Chat Message Flow

1. **ChatMessage received** → ACK immediately
2. **Check if sender has pending confirmation**:
   - YES → Process confirmation response (yes/no)
   - NO → Continue to question processing
3. **Check if help request**:
   - YES → Send help message, end session
   - NO → Continue to question processing
4. **Auto-detect category** using keyword matching
5. **Send processing notification** to user
6. **Create MarketRequest** from natural language
7. **Call existing pipeline** (`handle_market_request`)
8. **Wait for DecisionResponse** (async)
9. **Send confirmation prompt** to user
10. **Store in pending_confirmations**
11. **Wait for user response** (next ChatMessage)
12. **Execute or cancel** based on response

### Category Detection Algorithm

```python
def detect_category(question: str) -> str:
    question_lower = question.lower()

    # Sports keywords
    sports_keywords = ["win", "beat", "nba", "nfl", "world cup", ...]
    if any(keyword in question_lower for keyword in sports_keywords):
        return "sports"

    # Financial keywords
    financial_keywords = ["bitcoin", "stock", "s&p", "crypto", ...]
    if any(keyword in question_lower for keyword in financial_keywords):
        return "financial"

    # Default to culture
    return "culture"
```

### Confirmation Handler Logic

```python
if sender in pending_confirmations:
    user_response = user_text.lower()

    if user_response in ["yes", "y", "confirm", "execute"]:
        # Get confirmation data
        confirmation_data = pending_confirmations[sender]

        # Send ExecuteTradeRequest to Kalshi agent
        await ctx.send(kalshi_agent_addr, trade_request)

        # Notify user
        await ctx.send(sender, ChatMessage("Trade execution initiated"))

        # Clean up and end session
        del pending_confirmations[sender]

    elif user_response in ["no", "n", "cancel", "abort"]:
        # Notify user of cancellation
        await ctx.send(sender, ChatMessage("Trade cancelled"))

        # Clean up and end session
        del pending_confirmations[sender]

    else:
        # Invalid response - ask again
        await ctx.send(sender, ChatMessage("Invalid response. Please reply 'yes' or 'no'"))
```

## Files Modified

### `/Users/sewonmyung/BerkeleyAIHackathon2026/uagents_deploy/orchestrator_agent.py`

**Changes:**
1. Added `pending_confirmations` state dict
2. Added `detect_category()` function
3. Rewrote help message for natural language examples
4. Added confirmation check at start of chat handler
5. Added natural language processing logic
6. Modified `handle_decision_response` to send confirmation prompt instead of final result
7. Added `"kalshi"` to AGENT_ADDRESSES

**Total lines changed:** ~150 lines

### `/Users/sewonmyung/BerkeleyAIHackathon2026/start_orchestrator.sh`

**Changes:**
1. Added KALSHI_AGENT_ADDRESS configuration section

## Dependencies

### Python Packages
- `uagents` - Fetch.ai agent framework
- `uagents[chat]` - ASI:One chat protocol support

### Required Deployed Agents
- **sports_video_agent.py** - Evidence collection (sports)
- **financial_research_agent.py** - Evidence collection (financial)
- **standalone_compression_agent.py** - Context compression
- **standalone_decision_agent.py** - Trading decisions
- **standalone_kalshi_agent.py** - Trade execution

## Deployment Checklist

- [ ] Deploy compression agent, get address
- [ ] Deploy decision agent, get address
- [ ] Deploy Kalshi agent, get address
- [ ] Set all environment variables in terminal or .env
- [ ] Run `./start_orchestrator.sh`
- [ ] Verify logs show "ASI:One chat protocol: ENABLED"
- [ ] Connect to mailbox via Agentverse Inspector
- [ ] Test with natural language question
- [ ] Verify decision prompt appears
- [ ] Test confirmation (reply "yes" or "no")
- [ ] Verify trade execution or cancellation

## Next Steps

1. **Deploy remaining agents** (compression, decision, Kalshi)
2. **Test the full pipeline** with a sports question
3. **Test the full pipeline** with a financial question
4. **Verify trade confirmation flow** works correctly
5. **Add timeout mechanism** for pending confirmations (expire after 5 minutes)
6. **Add trade execution result handler** to show Kalshi response to user

## Known Limitations

1. **No timeout on confirmations** - Pending confirmations never expire (TODO: add 5-minute timeout)
2. **No trade execution result display** - User doesn't see Kalshi agent's response yet (TODO: add handler)
3. **Single pending confirmation** - Can only have one pending trade per user at a time (by design)
4. **Basic category detection** - Keyword-based, may misclassify edge cases (could improve with ML)
5. **Fixed trade quantity** - Always trades 1 contract (TODO: let user specify quantity)

## Future Enhancements

1. **Confirmation timeout** - Auto-cancel after 5 minutes
2. **Trade size input** - "How many contracts?" prompt
3. **Multiple confirmation tracking** - Support multiple pending trades per user
4. **Kalshi result display** - Show execution results from Kalshi agent
5. **Trade history** - Store and display past trades
6. **Portfolio tracking** - Show user's current positions
7. **Multi-turn conversation** - Allow follow-up questions before trading
8. **NLP improvements** - Better category detection, entity extraction
9. **Voice support** - Accept audio questions (if DeltaV supports)
10. **Risk warnings** - Show position sizing recommendations

## Success Criteria

✅ **COMPLETED:**
- [x] Natural language input processing
- [x] Auto-category detection
- [x] Evidence collection from multiple agents
- [x] Compression and decision pipeline
- [x] Interactive confirmation prompts
- [x] Yes/no response handling
- [x] Kalshi agent integration
- [x] Trade cancellation support

⏳ **IN PROGRESS:**
- [ ] Deploy compression agent
- [ ] Deploy decision agent
- [ ] Deploy Kalshi agent
- [ ] Test full pipeline end-to-end

📋 **TODO:**
- [ ] Add confirmation timeout
- [ ] Display Kalshi execution results
- [ ] Support trade quantity input
- [ ] Add error recovery for agent failures

---

**Last Updated:** 2026-06-20

**Status:** ✅ Implementation Complete - Ready for Testing
