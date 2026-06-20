## Agentverse Deployment Guide

This guide explains how to deploy the multi-agent prediction market system to Fetch.ai's Agentverse platform.

## Overview

The system consists of 4 main agents (implemented) + 4 placeholder agents (future):

**Implemented:**
1. `OrchestratorAgent` - User-facing coordinator (Port 8000)
2. `CultureWebAgent` - Evidence collector (Port 8001)
3. `CompressionAgent` - Context compressor (Port 8002)
4. `DecisionAgent` - Trading decision maker (Port 8003)

**Placeholders:**
5. `SportsVideoAgent` (Port 8004)
6. `PoliticsNewsAgent` (Port 8005)
7. `FinancialResearchAgent` (Port 8006)
8. `MarketAgent` (Port 8007)

## Prerequisites

1. **Agentverse Account**
   - Sign up at [https://agentverse.ai](https://agentverse.ai)
   - Access the Agent Inspector

2. **Install Dependencies**
   ```bash
   pip install uagents>=0.12.0
   ```

## Deployment Steps

### Step 1: Prepare Agent Files

Each agent needs a unique seed phrase for production. Update the seed in each agent file:

```python
# BEFORE (development)
AGENT_SEED = "culture_web_agent_seed_phrase_change_in_production"

# AFTER (production)
AGENT_SEED = "your_unique_production_seed_phrase_here_xxxxxxx"
```

**Generate unique seeds:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Deploy to Agentverse

For each agent, follow these steps:

1. **Upload Agent Code**
   - In Agentverse UI, create a new agent
   - Copy the agent code from the `.py` file
   - Paste into the Agentverse editor
   - Include the `protocols/messages.py` content as well

2. **Enable Mailbox**
   - In Agent Settings, enable "Mailbox"
   - This allows agents to communicate asynchronously

3. **Publish Agent**
   - Click "Publish" to make the agent live
   - Note the agent address (format: `agent_xxx@agentverse.ai`)

4. **Repeat for All Agents**
   - Deploy: `culture_web_agent.py`
   - Deploy: `compression_agent.py`
   - Deploy: `decision_agent.py`
   - Deploy: `orchestrator_agent.py`

### Step 3: Configure Agent Addresses

After deploying all agents, update `agent_config.py` with the actual addresses:

```python
AGENT_ADDRESSES = {
    "culture_web_agent": "agent_<ID1>@agentverse.ai",
    "compression_agent": "agent_<ID2>@agentverse.ai",
    "decision_agent": "agent_<ID3>@agentverse.ai",
    "orchestrator_agent": "agent_<ID4>@agentverse.ai",
}
```

Or use environment variables:

```bash
export CULTURE_WEB_AGENT_ADDRESS="agent_<ID1>@agentverse.ai"
export COMPRESSION_AGENT_ADDRESS="agent_<ID2>@agentverse.ai"
export DECISION_AGENT_ADDRESS="agent_<ID3>@agentverse.ai"
export ORCHESTRATOR_AGENT_ADDRESS="agent_<ID4>@agentverse.ai"
```

### Step 4: Update Agent Code with Addresses

After deploying, update the `AGENT_ADDRESSES` dictionary in `orchestrator_agent.py` to include the real addresses:

```python
# In orchestrator_agent.py
AGENT_ADDRESSES = {
    "culture_web": "agent_<ID1>@agentverse.ai",
    "compression": "agent_<ID2>@agentverse.ai",
    "decision": "agent_<ID3>@agentverse.ai",
}
```

Re-upload the updated orchestrator agent code to Agentverse.

### Step 5: Test Communication

Send a test `MarketRequest` to the orchestrator:

```python
from protocols.messages import MarketRequest
from uagents import Agent, Context

# Create a test client agent
test_agent = Agent(name="test_client", seed="test_seed")

@test_agent.on_interval(period=60.0)
async def send_test_request(ctx: Context):
    orchestrator_addr = "agent_<ORCHESTRATOR_ID>@agentverse.ai"

    market_request = MarketRequest(
        market_id="test-market",
        market_title="Will 'Stellar Dreams' win Best Picture?",
        market_question="Will the film 'Stellar Dreams' win the Academy Award for Best Picture?",
        category="culture",
        current_yes_price=0.42,
        current_no_price=0.58,
        resolution_criteria="Market resolves YES if film wins.",
        protected_terms=["Stellar Dreams", "Best Picture", "Academy Awards"]
    )

    await ctx.send(orchestrator_addr, market_request)
    ctx.logger.info("Test request sent to orchestrator")

if __name__ == "__main__":
    test_agent.run()
```

### Step 6: Monitor Agent Logs

In the Agentverse UI, check the logs for each agent to verify:

- Agents are receiving messages
- Agents are processing requests
- Agents are sending responses
- No errors in the pipeline

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                           User                               │
│                            ↓                                 │
│                   OrchestratorAgent                          │
│                   (agentverse.ai)                            │
│                            ↓                                 │
│           ┌────────────────┼────────────────┐               │
│           ↓                ↓                ↓               │
│    CultureWebAgent  SportsVideoAgent  PoliticsNewsAgent    │
│    (agentverse.ai)  (agentverse.ai)   (agentverse.ai)      │
│           ↓                                                  │
│    CompressionAgent                                          │
│    (agentverse.ai)                                          │
│           ↓                                                  │
│    DecisionAgent                                             │
│    (agentverse.ai)                                          │
│           ↓                                                  │
│    FinalAnalysisResult → User                               │
└─────────────────────────────────────────────────────────────┘
```

## Benefits of Agentverse Deployment

1. **Always Online**: Agents run 24/7 without needing your local machine
2. **Automatic Discovery**: Agents can find each other via the Almanac
3. **Scalability**: Agentverse handles scaling and load balancing
4. **Mailbox System**: Asynchronous message delivery even when agents are busy
5. **Monitoring**: Built-in logging and monitoring tools
6. **Version Control**: Easy to update and rollback agent versions

## Message Flow

1. **User → Orchestrator**: `MarketRequest`
2. **Orchestrator → CultureWebAgent**: `EvidenceRequest`
3. **CultureWebAgent → Orchestrator**: `EvidenceResponse` (evidence chunks)
4. **Orchestrator → CompressionAgent**: `CompressionRequest` (all evidence)
5. **CompressionAgent → Orchestrator**: `CompressionResponse` (compressed context)
6. **Orchestrator → DecisionAgent**: `DecisionRequest` (compressed context)
7. **DecisionAgent → Orchestrator**: `DecisionResponse` (YES/NO/HOLD)
8. **Orchestrator → User**: `FinalAnalysisResult`

## Troubleshooting

### Agents Not Communicating

**Problem**: Agents send messages but don't receive responses.

**Solutions**:
- Verify mailbox is enabled for all agents
- Check agent addresses are correct
- Ensure all agents are published and running
- Check agent logs for errors

### Import Errors

**Problem**: Agent can't import from `protocols.messages`

**Solution**:
- Copy the contents of `protocols/messages.py` into each agent file
- Or use Agentverse's package management to include the protocols module

### Timeout Errors

**Problem**: Orchestrator times out waiting for agent responses

**Solution**:
- Increase timeout values in orchestrator
- Check if downstream agents are running
- Verify agent addresses are correct

### Missing Data Files

**Problem**: CultureWebAgent can't find sample data file

**Solution**:
- For Agentverse deployment, embed sample data directly in the agent code
- Or upload sample files to a cloud storage and reference URLs
- Or use Browserbase integration for live data collection

## Next Steps

After successful deployment:

1. **Monitor Performance**: Track compression ratios and decision accuracy
2. **Add More Agents**: Deploy SportsVideoAgent, PoliticsNewsAgent, etc.
3. **Integrate Real Services**: Connect Browserbase, Kalshi, etc.
4. **Build Frontend**: Create a web UI to interact with the orchestrator
5. **Track Metrics**: Monitor agent performance and optimize scoring algorithms

## Support

- [Fetch.ai Discord](https://discord.gg/fetchai)
- [uAgents Documentation](https://uagents.fetch.ai)
- [Agentverse Help Center](https://agentverse.ai/help)
