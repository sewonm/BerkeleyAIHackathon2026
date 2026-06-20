# uAgents Deployment - Multi-Agent Prediction Market System

This directory contains standalone Fetch.ai uAgents that can be deployed to **Agentverse** as independent services.

## Architecture

The system uses a **multi-agent architecture** where each agent has a single responsibility:

```
User
  ↓
OrchestratorAgent (User-Facing)
  ↓
  ├──→ CultureWebAgent       → Evidence Collection
  ├──→ SportsVideoAgent      → Evidence Collection (placeholder)
  ├──→ PoliticsNewsAgent     → Evidence Collection (placeholder)
  └──→ FinancialResearchAgent → Evidence Collection (placeholder)
  ↓
CompressionAgent → Context Compression
  ↓
DecisionAgent → Trading Decision
  ↓
Back to User with FinalAnalysisResult
```

## Agents

### ✅ Implemented Agents

1. **OrchestratorAgent** (`orchestrator_agent.py`)
   - **Port**: 8000
   - **Role**: User-facing coordinator
   - **Function**: Receives market analysis requests, coordinates evidence collection, compression, and decision-making
   - **Agentverse**: Deploy this as your public-facing agent

2. **CultureWebAgent** (`culture_web_agent.py`)
   - **Port**: 8001
   - **Role**: Evidence collector for culture/entertainment
   - **Function**: Collects evidence from culture, entertainment, streaming, box office, awards sources
   - **MVP**: Reads from local sample file
   - **Production**: Would integrate with Browserbase for live web scraping

3. **CompressionAgent** (`compression_agent.py`)
   - **Port**: 8002
   - **Role**: Context compression service
   - **Function**: Takes raw evidence chunks, scores them, deduplicates, and compresses into decision-ready context
   - **Key Feature**: Implements the Token Compression Challenge solution

4. **DecisionAgent** (`decision_agent.py`)
   - **Port**: 8003
   - **Role**: Trading decision maker
   - **Function**: Analyzes compressed evidence and outputs YES/NO/HOLD recommendations with confidence scores

### 📋 Placeholder Agents (Future Implementation)

5. **SportsVideoAgent** (`sports_video_agent.py`) - Port 8004
6. **PoliticsNewsAgent** - Port 8005
7. **FinancialResearchAgent** - Port 8006
8. **MarketAgent** - Port 8007

## Message Protocols

All agents communicate using standardized Pydantic message models defined in `protocols/messages.py`:

- `MarketRequest` / `FinalAnalysisResult` - User ↔ Orchestrator
- `EvidenceRequest` / `EvidenceResponse` - Orchestrator ↔ Evidence Agents
- `CompressionRequest` / `CompressionResponse` - Orchestrator ↔ Compression Agent
- `DecisionRequest` / `DecisionResponse` - Orchestrator ↔ Decision Agent
- `AgentStatus` - Status updates from any agent

## Local Development

### Installation

```bash
# Install dependencies
pip install uagents pydantic python-dotenv

# Or from project root
pip install -r requirements.txt
```

### Running Agents Locally

Each agent can run independently. Open separate terminals for each:

```bash
# Terminal 1: Culture Web Agent
cd uagents_deploy
python culture_web_agent.py

# Terminal 2: Compression Agent
python compression_agent.py

# Terminal 3: Decision Agent
python decision_agent.py

# Terminal 4: Orchestrator (user-facing)
python orchestrator_agent.py
```

### Configuration

Update agent addresses in `agent_config.py` or via environment variables:

```bash
export CULTURE_WEB_AGENT_ADDRESS="agent_xxx@agentverse.ai"
export COMPRESSION_AGENT_ADDRESS="agent_yyy@agentverse.ai"
export DECISION_AGENT_ADDRESS="agent_zzz@agentverse.ai"
export ORCHESTRATOR_AGENT_ADDRESS="agent_aaa@agentverse.ai"
```

## Agentverse Deployment

### Step-by-Step Deployment

1. **Create Account on Agentverse**
   - Go to https://agentverse.ai
   - Create an account
   - Access the Agent Inspector

2. **Deploy Each Agent**

For each agent file (`culture_web_agent.py`, `compression_agent.py`, etc.):

```bash
# Change the seed phrase for production deployment
# In each agent file, update:
AGENT_SEED = "your_unique_production_seed_phrase_here"
```

3. **Enable Mailbox**
   - In Agentverse UI, enable mailbox for each agent
   - This allows agents to communicate even when not directly networked

4. **Publish Agent Manifests**
   - Agents will automatically register with the Almanac
   - Note down each agent's address (format: `agent_xxx@agentverse.ai`)

5. **Update Agent Configuration**

Update `agent_config.py` with the deployed addresses:

```python
AGENT_ADDRESSES = {
    "culture_web_agent": "agent_xxx@agentverse.ai",
    "compression_agent": "agent_yyy@agentverse.ai",
    "decision_agent": "agent_zzz@agentverse.ai",
    "orchestrator_agent": "agent_aaa@agentverse.ai",
}
```

6. **Test Communication**

Send a test `MarketRequest` to the orchestrator agent's address.

## Message Flow Example

```python
# User sends MarketRequest to Orchestrator
MarketRequest {
    market_id: "sample-culture-oscars",
    market_title: "Will Movie X win Best Picture?",
    category: "culture",
    ...
}

# Orchestrator → CultureWebAgent: EvidenceRequest
# CultureWebAgent → Orchestrator: EvidenceResponse (49 chunks)

# Orchestrator → CompressionAgent: CompressionRequest
# CompressionAgent → Orchestrator: CompressionResponse (compressed 8.5x)

# Orchestrator → DecisionAgent: DecisionRequest
# DecisionAgent → Orchestrator: DecisionResponse (YES, 75% confidence)

# Orchestrator → User: FinalAnalysisResult
```

## Agent Independence

Each agent is fully independent and can be:

- **Deployed separately** to different Agentverse instances
- **Scaled independently** based on load
- **Updated independently** without affecting other agents
- **Replaced** with different implementations (e.g., swap in an LLM-based decision agent)

## Future Enhancements

### Integration with Real Services

Each agent can be enhanced with real service integrations:

- **CultureWebAgent**: Integrate Browserbase for live web scraping
- **CompressionAgent**: Add ML-based relevance scoring
- **DecisionAgent**: Integrate LLM APIs (OpenAI, Anthropic) for advanced reasoning
- **MarketAgent**: Connect to Kalshi API for real market data
- **SportsVideoAgent**: Integrate video analysis APIs
- **PoliticsNewsAgent**: Connect to news APIs
- **FinancialResearchAgent**: Integrate financial data providers

### Multi-Agent Coordination

Expand orchestration to:

- **Parallel evidence collection** from multiple agents
- **Consensus mechanisms** between multiple decision agents
- **Dynamic agent selection** based on market category
- **Agent reputation tracking** based on prediction accuracy
- **Automated retraining** of agents based on market outcomes

## Hackathon Demo

For the hackathon demo, you can:

1. **Show the architecture** - Explain how each agent is independent
2. **Run locally** - Demo the multi-agent pipeline running on localhost
3. **Deploy one agent** - Show how to deploy the Orchestrator to Agentverse
4. **Explain scalability** - Each agent can be deployed and scaled independently
5. **Highlight Token Compression** - The CompressionAgent showcases the compression challenge solution

## Benefits of uAgents Architecture

1. **Modularity**: Each agent has one job, making the system easy to understand and maintain
2. **Scalability**: Agents can be scaled independently based on load
3. **Resilience**: If one agent fails, others continue working
4. **Flexibility**: Agents can be swapped out or upgraded without affecting the system
5. **Decentralization**: Agents can run on different machines/cloud providers
6. **Agentverse Integration**: Easy deployment to Fetch.ai's agent marketplace

## Troubleshooting

### Agents Can't Communicate

- Ensure all agents have mailbox enabled in Agentverse
- Verify agent addresses are correct in `agent_config.py`
- Check that agents are running and listening on their ports

### Missing Dependencies

```bash
pip install uagents pydantic python-dotenv
```

### Import Errors

Ensure you're running from the project root or add to Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Links

- [Fetch.ai uAgents Documentation](https://uagents.fetch.ai/docs)
- [Agentverse Platform](https://agentverse.ai)
- [uAgents GitHub](https://github.com/fetchai/uAgents)
- [ASI-1 Example](https://uagents.fetch.ai/docs/examples/asi-1)
