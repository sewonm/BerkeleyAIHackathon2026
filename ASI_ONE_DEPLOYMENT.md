# ASI:One Compatible Agent Deployment Guide

Complete guide for deploying your three ASI:One compatible agents to Agentverse and DeltaV.

---

## What is ASI:One?

**ASI:One** is Fetch.ai's standard protocol for making agents discoverable and interoperable across the ecosystem. Agents that follow ASI:One can be:

- **Discovered on DeltaV** - Fetch.ai's AI-powered assistant marketplace
- **Found via Agentverse Almanac** - Agent directory
- **Interoperable** - Work with other ASI:One compatible agents
- **User-Friendly** - Accept natural language or structured JSON requests

---

## Your Three ASI:One Compatible Agents

All three agents now support **dual protocols**:

### 1. **Compression Agent** (`standalone_compression_agent.py`)

**Custom Protocol**: `StandaloneContextCompression` (agent-to-agent)
**Chat Protocol**: ASI:One compatible (DeltaV/user interaction)

**What it does**:
- Compresses evidence chunks using graph-consensus algorithm
- Extracts claims and builds evidence graph
- Identifies consensus, contradictions, and missing information
- Returns compressed context optimized for trading decisions

**Input formats**:
- JSON with market data and evidence chunks
- Natural language queries (returns help)

**Outputs**:
- Compressed context with YES/NO evidence
- Compression metrics (ratio, token counts)
- Consensus items with information value scores
- Contradictions and missing information

---

### 2. **Decision Agent** (`standalone_decision_agent.py`)

**Custom Protocol**: `StandaloneTradingDecision` (agent-to-agent)
**Chat Protocol**: ASI:One compatible (DeltaV/user interaction)

**What it does**:
- Analyzes compressed context
- Estimates fair value using Claude reasoning
- Calculates edge (fair value - market price)
- Determines trading action (BUY_YES/BUY_NO/HOLD)
- Sizes position using Kelly Criterion

**Input formats**:
- JSON with market question, compressed context, risk tolerance
- Natural language queries (returns help)

**Outputs**:
- Trading decision with confidence
- Fair value estimate
- Edge calculation
- Suggested position size
- Detailed reasoning and risk factors

---

### 3. **Kalshi Execution Agent** (`standalone_kalshi_agent.py`)

**Custom Protocol**: `KalshiExecution` (agent-to-agent)
**Chat Protocol**: ASI:One compatible (DeltaV/user interaction)

**What it does**:
- Connects to Kalshi API
- Places orders (market or limit)
- Monitors order execution
- Reports fill price, fees, status

**Input formats**:
- JSON with market_id, action, quantity, order_type
- Natural language queries (returns help)

**Outputs**:
- Order ID and status
- Fill price and executed quantity
- Platform fees and total cost
- Execution time

---

## How ASI:One Integration Works

### Dual Protocol Architecture

Each agent includes TWO protocols:

```python
# Protocol 1: Custom (agent-to-agent communication)
compression_protocol = Protocol("StandaloneContextCompression")
agent.include(compression_protocol, publish_manifest=False)  # Internal only

# Protocol 2: ASI:One Chat (DeltaV/user interaction)
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol("Chat", spec=chat_protocol_spec)
    agent.include(chat_protocol, publish_manifest=True)  # Publicly discoverable
```

### Message Flow

**Agent-to-Agent Communication** (Custom Protocol):
```
Compression Agent → Decision Agent → Kalshi Agent
   (via custom protocol messages)
```

**DeltaV/User Communication** (Chat Protocol):
```
User/DeltaV → [ChatMessage] → Agent
Agent → [ChatAcknowledgement] → User/DeltaV
Agent → [ChatMessage with TextContent] → User/DeltaV
Agent → [ChatMessage with EndSessionContent] → User/DeltaV
```

### Chat Message Pattern

All chat handlers follow this pattern:

```python
@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    # 1. Send acknowledgement
    await ctx.send(sender, ChatAcknowledgement())

    # 2. Extract text from message
    user_text = ""
    for content in msg.content:
        if isinstance(content, TextContent):
            user_text += content.text

    # 3. Try to parse as JSON (structured request)
    try:
        request_data = json.loads(user_text)
        # Process request...
        response = ChatMessage(content=[TextContent(text=result)])
        await ctx.send(sender, response)

    # 4. If not JSON, provide help
    except json.JSONDecodeError:
        help_text = """..."""
        response = ChatMessage(content=[TextContent(text=help_text)])
        await ctx.send(sender, response)

    # 5. Always end session
    finally:
        await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
```

---

## Deployment to Agentverse

### Step 1: Prepare Environment Variables

```bash
# Optional for Compression & Decision agents (Claude reasoning)
ANTHROPIC_API_KEY=your_claude_api_key

# Required for Kalshi agent
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Use demo for testing
```

### Step 2: Deploy Each Agent

**For EACH of the 3 agents:**

1. **Go to Agentverse**: https://agentverse.ai/

2. **Create New Agent**:
   - Click "Create Agent" or "New Agent"

3. **Select Protocol**:
   - ✅ **Select: "Agent Chat Protocol (ASI) - Discoverable"**
   - This enables ASI:One compatibility and DeltaV discovery

4. **Upload Agent Code**:
   - **Compression Agent**: Upload `uagents_deploy/standalone_compression_agent.py`
   - **Decision Agent**: Upload `uagents_deploy/standalone_decision_agent.py`
   - **Kalshi Agent**: Upload `uagents_deploy/standalone_kalshi_agent.py`

5. **Configure Agent Details**:
   ```
   Name: compression-agent-yourname
   Description: Graph-consensus context compression for prediction markets

   Name: decision-agent-yourname
   Description: Trading decision engine with Kelly Criterion position sizing

   Name: kalshi-agent-yourname
   Description: Kalshi API execution agent for automated trading
   ```

6. **Set Environment Variables** (in Agentverse UI):
   - For Compression & Decision: `ANTHROPIC_API_KEY` (optional)
   - For Kalshi: `KALSHI_EMAIL`, `KALSHI_PASSWORD`, `KALSHI_USE_DEMO`

7. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete (green status)
   - **Copy the agent address** (starts with `agent1q...`)

8. **Verify ASI:One Status**:
   - Check agent logs for:
     ```
     Custom protocol: ENABLED (agent-to-agent communication)
     ASI:One chat protocol: ENABLED (DeltaV compatible)
     ```

### Step 3: Get Agent Addresses

After deploying all three agents, you'll have:

```python
COMPRESSION_AGENT = "agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x..."  # From Agentverse
DECISION_AGENT = "agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z..."      # From Agentverse
KALSHI_AGENT = "agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c..."        # From Agentverse
```

**Save these addresses** - you'll use them for orchestration or testing.

---

## Testing ASI:One Agents

### Method 1: Test via DeltaV

1. **Go to DeltaV**: https://deltav.agentverse.ai/

2. **Search for your agent** by name or description

3. **Send natural language query**:
   ```
   "Help me compress evidence for prediction markets"
   ```

4. **Agent responds with help message**:
   ```markdown
   **Compression Agent**

   I compress large evidence contexts for prediction market trading...

   **How to use me**: Send JSON with...
   ```

5. **Send structured JSON request**:
   ```json
   {
     "market_question": "Will France win the World Cup?",
     "evidence_chunks": [...]
   }
   ```

6. **Receive compressed response**

### Method 2: Test via uAgent Client

Create a test client that sends ChatMessages:

```python
from uagents import Agent, Context
from uagents.chat import ChatMessage, TextContent

test_client = Agent(name="test_client", seed="test123", port=9000)

COMPRESSION_AGENT = "agent1qw5z..."  # Your deployed agent address

@test_client.on_event("startup")
async def send_chat_request(ctx: Context):
    # Send natural language query
    message = ChatMessage(
        content=[TextContent(text="How do I use you?")]
    )
    await ctx.send(COMPRESSION_AGENT, message)

@test_client.on_message(model=ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    for content in msg.content:
        if isinstance(content, TextContent):
            print(f"Response: {content.text}")

test_client.run()
```

### Method 3: Test Agent-to-Agent Communication

Use the original custom protocols for agent-to-agent flow:

```python
from uagents import Agent, Context

orchestrator = Agent(name="orchestrator", seed="orch123", port=8001)

COMPRESSION_AGENT = "agent1qw5z..."
DECISION_AGENT = "agent1qx3j..."
KALSHI_AGENT = "agent1qy7k..."

@orchestrator.on_event("startup")
async def run_pipeline(ctx: Context):
    # Use custom protocol (not chat protocol)
    compression_request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will France win the World Cup?",
        evidence_chunks=[...]
    )
    await ctx.send(COMPRESSION_AGENT, compression_request)

# Handle responses with custom protocol messages
@orchestrator.on_message(model=EnhancedCompressionResponse)
async def handle_compression(ctx: Context, sender: str, msg: EnhancedCompressionResponse):
    # Send to decision agent...
    decision_request = TradingDecisionRequest(
        compressed_context=msg.compression_result.compressed_context,
        ...
    )
    await ctx.send(DECISION_AGENT, decision_request)

# Continue pipeline...
```

---

## Graceful Degradation

All agents gracefully handle missing `uagents.chat` package:

```python
try:
    from uagents.chat import (...)
    CHAT_PROTOCOL_AVAILABLE = True
except ImportError:
    print("[Warning] Chat protocol not available - ASI:One integration disabled")
    CHAT_PROTOCOL_AVAILABLE = False
```

**If chat protocol is unavailable**:
- ✅ Agents still work with custom protocols (agent-to-agent)
- ❌ DeltaV discovery disabled
- ❌ Chat message handling disabled

**To enable chat protocol**:
```bash
pip install uagents[chat]
```

Or install from source if not available in package.

---

## Pre-Deployment Checklist

### ✅ Code Ready
- [x] All three agents have ASI:One chat protocol support
- [x] All agents have `publish_agent_details=True`
- [x] Dual protocols included (custom + chat)
- [x] Chat message handlers implemented
- [x] Graceful degradation for missing chat package

### ✅ Environment Variables
- [ ] `ANTHROPIC_API_KEY` (optional, for Claude reasoning)
- [ ] `KALSHI_EMAIL` (required for Kalshi agent)
- [ ] `KALSHI_PASSWORD` (required for Kalshi agent)
- [ ] `KALSHI_USE_DEMO=true` (recommended for testing)

### ✅ Local Testing
- [ ] Run compression agent: `cd uagents_deploy && python standalone_compression_agent.py`
- [ ] Run decision agent: `cd uagents_deploy && python standalone_decision_agent.py`
- [ ] Run Kalshi agent: `cd uagents_deploy && python standalone_kalshi_agent.py`
- [ ] Check logs for "ASI:One chat protocol: ENABLED"

### ✅ Agentverse Deployment
- [ ] Select "Agent Chat Protocol (ASI) - Discoverable"
- [ ] Upload each agent file
- [ ] Set environment variables
- [ ] Deploy and verify green status
- [ ] Copy all three agent addresses

### ✅ DeltaV Testing
- [ ] Search for agents on DeltaV
- [ ] Send natural language query
- [ ] Verify help message received
- [ ] Send JSON request
- [ ] Verify structured response

---

## Expected Startup Logs

### Compression Agent
```
[standalone_compression_agent] Standalone Compression Agent started!
Address: agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x...
Mode: Graph-Consensus Compression
Ready to compress evidence contexts
Custom protocol: ENABLED (agent-to-agent communication)
ASI:One chat protocol: ENABLED (DeltaV compatible)
Claude extraction: ENABLED
```

### Decision Agent
```
[decision_agent_standalone] Standalone Decision Agent started!
Address: agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z...
Ready to make trading decisions
Custom protocol: ENABLED (agent-to-agent communication)
ASI:One chat protocol: ENABLED (DeltaV compatible)
Decision mode: Claude-based reasoning
```

### Kalshi Agent
```
[kalshi_execution_agent] Kalshi Execution Agent started!
Address: agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c...
Mode: DEMO
Ready to execute orders on Kalshi
Custom protocol: ENABLED (agent-to-agent communication)
ASI:One chat protocol: ENABLED (DeltaV compatible)
Logged in to Kalshi successfully
Account balance: $1000.00
```

---

## Troubleshooting

### Issue: "ASI:One chat protocol: DISABLED"

**Cause**: `uagents.chat` package not installed

**Fix**:
```bash
pip install uagents[chat]
```

Or continue without chat protocol (agent-to-agent still works).

### Issue: Agent not discoverable on DeltaV

**Causes**:
1. Did not select "Agent Chat Protocol (ASI) - Discoverable"
2. Chat protocol not enabled (`CHAT_PROTOCOL_AVAILABLE = False`)
3. Agent not deployed with `publish_manifest=True`

**Fix**:
1. Re-deploy with "Agent Chat Protocol (ASI)" option
2. Install `uagents[chat]`
3. Verify chat protocol included with `publish_manifest=True`

### Issue: "Import uagents.chat could not be resolved"

**Status**: Expected warning - this is a graceful degradation pattern

**Impact**: None if `uagents.chat` is installed on deployment server

**Fix**: Ignore warning if package will be available in production

### Issue: Agent responds but DeltaV session doesn't end

**Cause**: Missing `EndSessionContent`

**Fix**: Verify chat handler includes:
```python
finally:
    await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
```

---

## Summary

**Your ASI:One compatible agents**:

1. ✅ **Compression Agent** - Graph-consensus compression for evidence
2. ✅ **Decision Agent** - Trading decisions with Kelly Criterion
3. ✅ **Kalshi Agent** - Order execution on Kalshi API

**What they support**:
- ✅ Agent-to-agent communication (custom protocols)
- ✅ DeltaV/user interaction (ASI:One chat protocol)
- ✅ Natural language queries (returns help)
- ✅ Structured JSON requests (processes requests)
- ✅ Graceful degradation (works without chat package)

**Deployment**:
1. Select "Agent Chat Protocol (ASI) - Discoverable"
2. Upload standalone agent file
3. Set environment variables
4. Deploy and copy agent address
5. Test on DeltaV

**No additional orchestrator needed** - agents are independently discoverable and can be chained via their addresses.

---

## Next Steps

1. **Deploy all three agents** to Agentverse
2. **Test each agent** individually on DeltaV
3. **Create orchestrator** (optional) to chain agents together
4. **Monitor logs** for ASI:One protocol status
5. **Iterate** based on user feedback from DeltaV

For more details, see:
- **Deployment Guide**: `DEPLOYMENT_CHECKLIST.md`
- **Testing Guide**: `TESTING_SUMMARY.md`
- **Quick Start**: `QUICK_START_GUIDE.md`
- **ASI:One Docs**: https://uagents.fetch.ai/docs/examples/asi-1
