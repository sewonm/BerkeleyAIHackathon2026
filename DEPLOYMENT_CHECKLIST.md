# Agentverse Deployment Checklist

Complete guide for deploying your 3 standalone agents to Agentverse.

---

## ✅ Answer to Your Questions

### 1. **Do the standalone agents have uAgents setup?**

**YES! All three agents are fully configured:**

| Agent | File | uAgent Setup | Protocol | Port |
|-------|------|--------------|----------|------|
| **Compression** | `standalone_compression_agent.py` | ✅ Complete | `StandaloneContextCompression` | 8002 |
| **Decision** | `standalone_decision_agent.py` | ✅ Complete | `StandaloneTradingDecision` | 8003 |
| **Kalshi** | `standalone_kalshi_agent.py` | ✅ Complete | `KalshiExecution` | 8004 |

Each has:
- ✅ `from uagents import Agent, Context, Protocol`
- ✅ `agent = Agent(name, seed, port, mailbox)`
- ✅ `@protocol.on_message()` handlers
- ✅ `agent.include(protocol)`
- ✅ `@agent.on_event("startup")` handler
- ✅ `if __name__ == "__main__": agent.run()`

### 2. **Are they deployable? Am I missing API keys?**

**YES, they're deployable!** Here's what each needs:

#### Compression Agent ✅ **Ready (no required keys)**
```python
# Optional (will fallback to heuristics)
ANTHROPIC_API_KEY=your_claude_key
```

#### Decision Agent ✅ **Ready (no required keys)**
```python
# Optional (will fallback to heuristics)
ANTHROPIC_API_KEY=your_claude_key
```

#### Kalshi Agent ⚠️ **Requires credentials**
```python
# Required for Kalshi agent
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Use demo for testing
```

**Summary:**
- **Compression & Decision agents** → Work WITHOUT any keys (graceful fallback)
- **Kalshi agent** → Needs Kalshi credentials (but can test without deploying)

### 3. **Can orchestrator connect to subagents through their uAgent addresses?**

**YES! This is the standard pattern.** Here's how:

---

## Orchestrator ↔ Subagent Communication

### Method 1: Direct Address Communication (Simplest)

**After deploying to Agentverse, you'll get agent addresses:**

```python
# Addresses you'll get from Agentverse
COMPRESSION_AGENT_ADDR = "agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x..."
DECISION_AGENT_ADDR = "agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z..."
KALSHI_AGENT_ADDR = "agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c..."
```

**Orchestrator agent:**

```python
from uagents import Agent, Context, Protocol

orchestrator = Agent(
    name="orchestrator_agent",
    seed="orchestrator_seed_12345",
    port=8001,
)

# Store subagent addresses
COMPRESSION_AGENT = "agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x..."
DECISION_AGENT = "agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z..."
KALSHI_AGENT = "agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c..."

@orchestrator.on_event("startup")
async def handle_user_request(ctx: Context):
    # 1. Send to compression agent
    compression_request = EnhancedCompressionRequest(...)
    await ctx.send(COMPRESSION_AGENT, compression_request)

@orchestrator.on_message(model=EnhancedCompressionResponse)
async def handle_compression_response(ctx: Context, sender: str, msg: EnhancedCompressionResponse):
    # 2. Send to decision agent
    decision_request = TradingDecisionRequest(
        compressed_context=msg.compression_result.compressed_context,
        ...
    )
    await ctx.send(DECISION_AGENT, decision_request)

@orchestrator.on_message(model=TradingDecisionResponse)
async def handle_decision_response(ctx: Context, sender: str, msg: TradingDecisionResponse):
    # 3. Send to Kalshi agent
    if msg.decision.action != "HOLD":
        order_request = KalshiOrderRequest(...)
        await ctx.send(KALSHI_AGENT, order_request)

@orchestrator.on_message(model=KalshiOrderResponse)
async def handle_order_response(ctx: Context, sender: str, msg: KalshiOrderResponse):
    ctx.logger.info(f"Trade executed! Order ID: {msg.order_status.order_id}")
```

### Method 2: Discovery via Almanac (Advanced)

**Agents register with Fetch.ai Almanac (agent directory):**

```python
from uagents import Agent, Context
from uagents.network import get_almanac_contract

orchestrator = Agent(name="orchestrator", seed="seed123")

@orchestrator.on_event("startup")
async def discover_agents(ctx: Context):
    # Query Almanac for agents by protocol
    almanac = get_almanac_contract()

    # Find compression agents
    compression_agents = await almanac.get_agents_by_protocol(
        "StandaloneContextCompression"
    )

    if compression_agents:
        COMPRESSION_AGENT = compression_agents[0].address
        ctx.logger.info(f"Found compression agent: {COMPRESSION_AGENT}")
```

**For your use case:** Method 1 (Direct Address) is simpler and recommended.

---

## Deployment Steps

### Step 1: Prepare Environment Variables

Create a `.env` file or note these down:

```bash
# Optional for Compression & Decision agents
ANTHROPIC_API_KEY=your_claude_api_key

# Required for Kalshi agent
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true
```

### Step 2: Test Locally First

```bash
# Test compression agent
cd uagents_deploy
python standalone_compression_agent.py
# Should start without errors

# Test decision agent (separate terminal)
python standalone_decision_agent.py
# Should start without errors

# Test Kalshi agent (if you have credentials)
export KALSHI_EMAIL=test@example.com
export KALSHI_PASSWORD=testpass
export KALSHI_USE_DEMO=true
python standalone_kalshi_agent.py
# Should login successfully or gracefully handle missing credentials
```

### Step 3: Deploy to Agentverse

**For EACH agent:**

1. **Go to Agentverse**: https://agentverse.ai/

2. **Click "Create Agent"**

3. **Select Protocol Type:**
   - ✅ **Select: "Agent Chat Protocol (ASI) - Discoverable"**
   - This makes your agent findable by others

4. **Upload Agent Code:**
   - Click "Upload File" or copy-paste
   - **Compression Agent**: Upload `standalone_compression_agent.py`
   - **Decision Agent**: Upload `standalone_decision_agent.py`
   - **Kalshi Agent**: Upload `standalone_kalshi_agent.py`

5. **Configure Agent:**
   ```
   Name: compression-agent-yourname
   Description: Context compression with graph-consensus
   ```

6. **Set Environment Variables:**
   - Click "Environment Variables"
   - Add `ANTHROPIC_API_KEY` (optional)
   - For Kalshi agent, add `KALSHI_EMAIL`, `KALSHI_PASSWORD`, `KALSHI_USE_DEMO`

7. **Deploy:**
   - Click "Deploy"
   - Wait for deployment to complete
   - **Copy the agent address** (starts with `agent1q...`)

8. **Repeat for all 3 agents**

### Step 4: Get Agent Addresses

After deployment, you'll have:

```python
COMPRESSION_AGENT = "agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x..."  # From Agentverse
DECISION_AGENT = "agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z..."      # From Agentverse
KALSHI_AGENT = "agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c..."        # From Agentverse
```

**Save these!** You'll use them in your orchestrator.

### Step 5: Create Orchestrator Agent

Create `orchestrator_agent_final.py`:

```python
from uagents import Agent, Context, Protocol
from typing import Dict, Any
import os

# Import schemas (copy from standalone files or create shared module)
from standalone_compression_agent import EnhancedCompressionRequest, EnhancedCompressionResponse
from standalone_decision_agent import TradingDecisionRequest, TradingDecisionResponse
from standalone_kalshi_agent import KalshiOrderRequest, KalshiOrderResponse

# Agent addresses from Agentverse
COMPRESSION_AGENT = os.getenv("COMPRESSION_AGENT_ADDR", "agent1qw5z...")
DECISION_AGENT = os.getenv("DECISION_AGENT_ADDR", "agent1qx3j...")
KALSHI_AGENT = os.getenv("KALSHI_AGENT_ADDR", "agent1qy7k...")

# Create orchestrator
orchestrator = Agent(
    name="orchestrator_agent",
    seed="orchestrator_seed_change_in_production",
    port=8001,
    mailbox=True,
)

protocol = Protocol("TradingOrchestration")

# State management
pipeline_state: Dict[str, Any] = {}


@protocol.on_message(model=dict)  # Accept user requests
async def handle_user_request(ctx: Context, sender: str, msg: dict):
    """Handle user trading request"""
    ctx.logger.info(f"Received user request: {msg}")

    # Extract request
    market_question = msg.get("market_question")
    evidence_chunks = msg.get("evidence_chunks", [])

    # Store in state
    request_id = msg.get("request_id", str(uuid4()))
    pipeline_state[request_id] = {
        "original_request": msg,
        "sender": sender,
    }

    # Step 1: Send to compression agent
    compression_request = EnhancedCompressionRequest(
        request_id=request_id,
        market_id=msg.get("market_id"),
        market_question=market_question,
        resolution_criteria=msg.get("resolution_criteria"),
        current_yes_price=msg.get("current_yes_price"),
        current_no_price=msg.get("current_no_price"),
        evidence_chunks=evidence_chunks,
        aggressiveness=msg.get("aggressiveness", 0.5),
    )

    ctx.logger.info(f"Sending to compression agent: {COMPRESSION_AGENT}")
    await ctx.send(COMPRESSION_AGENT, compression_request)


@protocol.on_message(model=EnhancedCompressionResponse)
async def handle_compression_response(ctx: Context, sender: str, msg: EnhancedCompressionResponse):
    """Handle compression response"""
    ctx.logger.info(f"Received compression response: {msg.request_id}")

    if msg.status != "success":
        ctx.logger.error(f"Compression failed: {msg.error}")
        return

    # Store compressed context
    if msg.request_id in pipeline_state:
        pipeline_state[msg.request_id]["compressed_context"] = msg.compression_result.compressed_context

    # Step 2: Send to decision agent
    original = pipeline_state[msg.request_id]["original_request"]

    decision_request = TradingDecisionRequest(
        request_id=msg.request_id,
        market_id=msg.market_id,
        market_question=original["market_question"],
        resolution_criteria=original["resolution_criteria"],
        current_yes_price=original["current_yes_price"],
        current_no_price=original["current_no_price"],
        compressed_context=msg.compression_result.compressed_context,
        max_position_size=original.get("max_position_size", 100.0),
        risk_tolerance=original.get("risk_tolerance", "moderate"),
    )

    ctx.logger.info(f"Sending to decision agent: {DECISION_AGENT}")
    await ctx.send(DECISION_AGENT, decision_request)


@protocol.on_message(model=TradingDecisionResponse)
async def handle_decision_response(ctx: Context, sender: str, msg: TradingDecisionResponse):
    """Handle decision response"""
    ctx.logger.info(f"Received decision: {msg.decision.action}")

    if msg.status != "success":
        ctx.logger.error(f"Decision failed: {msg.error}")
        return

    # Store decision
    if msg.request_id in pipeline_state:
        pipeline_state[msg.request_id]["decision"] = msg.decision

    # Step 3: Execute trade if not HOLD
    if msg.decision.action == "HOLD":
        ctx.logger.info("Decision is HOLD, not executing trade")
        # Send final response to user
        await ctx.send(
            pipeline_state[msg.request_id]["sender"],
            {"status": "completed", "decision": "HOLD", "reasoning": msg.decision.reasoning}
        )
        return

    # Execute trade
    order_request = KalshiOrderRequest(
        request_id=msg.request_id,
        decision_id=msg.decision.decision_id,
        market_id=msg.market_id,
        action=msg.decision.action,
        quantity=int(msg.decision.suggested_position_size / 0.5),  # Rough estimate
        order_type="limit",
        limit_price=int(msg.decision.price_limit * 100) if msg.decision.price_limit else None,
    )

    ctx.logger.info(f"Sending to Kalshi agent: {KALSHI_AGENT}")
    await ctx.send(KALSHI_AGENT, order_request)


@protocol.on_message(model=KalshiOrderResponse)
async def handle_order_response(ctx: Context, sender: str, msg: KalshiOrderResponse):
    """Handle order execution response"""
    ctx.logger.info(f"Trade executed: {msg.order_status.status}")

    # Send final response to user
    if msg.request_id in pipeline_state:
        await ctx.send(
            pipeline_state[msg.request_id]["sender"],
            {
                "status": "completed",
                "order_id": msg.order_status.order_id,
                "order_status": msg.order_status.status,
                "decision": pipeline_state[msg.request_id]["decision"].action,
            }
        )


orchestrator.include(protocol)


@orchestrator.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("Orchestrator agent started!")
    ctx.logger.info(f"Compression agent: {COMPRESSION_AGENT}")
    ctx.logger.info(f"Decision agent: {DECISION_AGENT}")
    ctx.logger.info(f"Kalshi agent: {KALSHI_AGENT}")


if __name__ == "__main__":
    orchestrator.run()
```

### Step 6: Test End-to-End

Send a test request to your orchestrator:

```python
# test_orchestrator.py
from uagents import Agent, Context

test_client = Agent(name="test_client", seed="test123", port=9000)

ORCHESTRATOR_ADDR = "agent1q..."  # Your orchestrator address

@test_client.on_event("startup")
async def send_request(ctx: Context):
    request = {
        "request_id": "test123",
        "market_id": "KXPRESI-2024",
        "market_question": "Will Trump win 2024 election?",
        "resolution_criteria": "Resolves YES if Trump wins...",
        "current_yes_price": 0.52,
        "current_no_price": 0.48,
        "evidence_chunks": [
            {
                "market_id": "KXPRESI-2024",
                "source_agent": "test",
                "source_type": "news",
                "text": "Latest polls show Trump leading in swing states...",
            }
        ],
        "max_position_size": 50.0,
        "risk_tolerance": "moderate",
        "aggressiveness": 0.5,
    }

    await ctx.send(ORCHESTRATOR_ADDR, request)

test_client.run()
```

---

## Pre-Deployment Checklist

### ✅ Files Ready
- [ ] `standalone_compression_agent.py` - Self-contained, no imports
- [ ] `standalone_decision_agent.py` - Self-contained, no imports
- [ ] `standalone_kalshi_agent.py` - Self-contained, no imports

### ✅ Environment Variables
- [ ] `ANTHROPIC_API_KEY` (optional)
- [ ] `KALSHI_EMAIL` (for Kalshi agent)
- [ ] `KALSHI_PASSWORD` (for Kalshi agent)
- [ ] `KALSHI_USE_DEMO=true` (for testing)

### ✅ Local Testing
- [ ] All agents start without errors
- [ ] All tests pass: `pytest tests/test_advanced_compression.py -v`
- [ ] Demo runs successfully: `python -m app.compression.demo_advanced_compression`

### ✅ Agentverse Deployment
- [ ] Select "Agent Chat Protocol (ASI) - Discoverable"
- [ ] Upload agent files
- [ ] Set environment variables
- [ ] Deploy and get agent addresses

### ✅ Orchestrator Setup
- [ ] Store all 3 agent addresses
- [ ] Create orchestrator with communication logic
- [ ] Test end-to-end flow

---

## Summary

**Your questions answered:**

1. ✅ **uAgents setup?** YES - All 3 standalone agents have complete uAgent configuration
2. ✅ **Deployable?** YES - They're ready for Agentverse (only Kalshi needs credentials)
3. ✅ **Orchestrator connection?** YES - Use agent addresses from Agentverse to connect them

**No missing pieces!** Your agents are production-ready for Agentverse deployment.
