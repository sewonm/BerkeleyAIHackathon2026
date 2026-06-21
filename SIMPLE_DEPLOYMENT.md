# Simple Agentverse Deployment - Just Run the Script!

## TL;DR

You don't need to upload code to Agentverse UI. Just run the Python script locally and it **automatically registers** with Agentverse!

---

## How It Works

When you run a uAgent with:
- `mailbox=True`
- `publish_agent_details=True`
- `agent.include(protocol, publish_manifest=True)`

The agent **automatically**:
1. Connects to Agentverse
2. Registers itself in the Almanac
3. Becomes discoverable on DeltaV
4. Handles messages remotely via mailbox

No UI upload needed!

---

## Deployment Steps

### Step 1: Set Environment Variables

```bash
# Optional for Compression & Decision agents (enables Claude reasoning)
export ANTHROPIC_API_KEY=your_claude_api_key

# Required for Kalshi agent
export KALSHI_EMAIL=your_email@example.com
export KALSHI_PASSWORD=your_password
export KALSHI_USE_DEMO=true  # Use demo mode for testing
```

### Step 2: Run Each Agent

That's it - just run the Python scripts!

**Compression Agent**:
```bash
cd uagents_deploy
python3 standalone_compression_agent.py
```

**Decision Agent** (in separate terminal):
```bash
cd uagents_deploy
python3 standalone_decision_agent.py
```

**Kalshi Agent** (in separate terminal):
```bash
cd uagents_deploy
python3 standalone_kalshi_agent.py
```

### Step 3: Verify Registration

Look for these logs on startup:

```
[standalone_compression_agent] Standalone Compression Agent started!
Address: agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x...
Mode: Graph-Consensus Compression
Ready to compress evidence contexts
Custom protocol: ENABLED (agent-to-agent communication)
ASI:One chat protocol: ENABLED (DeltaV compatible)
Claude extraction: ENABLED
```

**Copy the agent address** - you'll see it in the logs!

### Step 4: Keep Agents Running

The agents need to stay running to process messages. You have options:

**Option A: Keep terminal open**
- Just leave the terminal windows open
- Agents run and process messages
- Good for testing

**Option B: Run in background**
```bash
nohup python3 standalone_compression_agent.py > compression.log 2>&1 &
nohup python3 standalone_decision_agent.py > decision.log 2>&1 &
nohup python3 standalone_kalshi_agent.py > kalshi.log 2>&1 &
```

**Option C: Use screen/tmux**
```bash
screen -S compression
python3 standalone_compression_agent.py
# Ctrl+A, D to detach

screen -S decision
python3 standalone_decision_agent.py
# Ctrl+A, D to detach

screen -S kalshi
python3 standalone_kalshi_agent.py
# Ctrl+A, D to detach
```

**Option D: Deploy to cloud server**
- AWS EC2, DigitalOcean, Google Cloud, etc.
- Keep agents running 24/7
- Use systemd or supervisor for process management

---

## How Mailbox Works

When a message comes from DeltaV or another agent:

1. **Message sent to your agent address**
2. **Agentverse mailbox receives it** (even if your script is temporarily offline)
3. **Your running agent fetches from mailbox** (when online)
4. **Agent processes and responds**
5. **Response goes through mailbox back to sender**

This is why you need:
- `mailbox=True` - Enables Agentverse mailbox
- Script running - To fetch and process messages
- Network connection - To communicate with Agentverse

---

## Testing on DeltaV

### Step 1: Find Your Agent

1. Go to **DeltaV**: https://deltav.agentverse.ai/
2. Search for your agent by the name in the code:
   - "standalone_compression_agent"
   - "decision_agent_standalone"
   - "kalshi_execution_agent"

### Step 2: Send a Message

**Natural language query**:
```
Help me compress evidence
```

**Structured request**:
```json
{
  "market_question": "Will France win the World Cup?",
  "evidence_chunks": [...]
}
```

### Step 3: Receive Response

Your agent will:
1. Receive the message via mailbox
2. Process it
3. Send response back through mailbox
4. You see the result in DeltaV

---

## Agent Addresses

After starting each agent, you'll see addresses like:

```python
# Compression Agent
Address: agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x...

# Decision Agent
Address: agent1qx3j9k2l5m8n0p2r4s6t8v0w2x4y6z...

# Kalshi Agent
Address: agent1qy7k3m5n7p9r1s3t5v7w9x1z3a5b7c...
```

**Save these addresses** for:
- Agent-to-agent communication
- Creating an orchestrator
- Testing with custom clients

---

## Production Deployment

For production (agents running 24/7), deploy to a server:

### Option 1: Cloud Server (AWS, DigitalOcean, etc.)

```bash
# SSH into server
ssh user@your-server.com

# Clone your repo
git clone https://github.com/yourusername/your-repo.git
cd your-repo/uagents_deploy

# Install dependencies
pip3 install uagents anthropic requests

# Set environment variables
export ANTHROPIC_API_KEY=...
export KALSHI_EMAIL=...
export KALSHI_PASSWORD=...

# Run agents with supervisor/systemd
# (see below for systemd example)
```

### Option 2: Systemd Service (Linux)

Create `/etc/systemd/system/compression-agent.service`:

```ini
[Unit]
Description=Compression Agent
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/BerkeleyAIHackathon2026/uagents_deploy
Environment="ANTHROPIC_API_KEY=your_key"
ExecStart=/usr/bin/python3 standalone_compression_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable compression-agent
sudo systemctl start compression-agent
sudo systemctl status compression-agent
```

Repeat for decision and kalshi agents.

### Option 3: Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY uagents_deploy/standalone_compression_agent.py .
RUN pip install uagents anthropic requests

ENV ANTHROPIC_API_KEY=""
CMD ["python3", "standalone_compression_agent.py"]
```

Build and run:
```bash
docker build -t compression-agent .
docker run -e ANTHROPIC_API_KEY=your_key compression-agent
```

---

## What About the Agentverse UI?

The Agentverse UI at https://agentverse.ai/ is for:
- **Viewing registered agents** - See agents in the Almanac
- **Hosted agents** - Upload code to run on Agentverse servers (alternative to running locally)
- **Monitoring** - View logs and status
- **Management** - Configure settings

But you **don't need it** for deployment if you:
- Run agents locally or on your own server
- Use `mailbox=True` and `publish_agent_details=True`
- Keep the script running

The agents auto-register themselves!

---

## Troubleshooting

### Issue: Agent not showing on DeltaV

**Check**:
1. Is the script still running? (Check terminal/logs)
2. Do logs show "ASI:One chat protocol: ENABLED"?
3. Is `publish_agent_details=True`? (Already set in your code ✅)
4. Is `publish_manifest=True` for chat protocol? (Already set ✅)

**Fix**: Keep script running and wait a few minutes for Almanac sync

### Issue: "ASI:One chat protocol: DISABLED"

**Cause**: Missing `uagents.chat` package

**Fix**:
```bash
pip install uagents
# If that doesn't include chat protocol:
pip install "uagents[chat]"
```

### Issue: Agent crashes or stops

**Check logs** for errors:
```bash
tail -f compression.log
tail -f decision.log
tail -f kalshi.log
```

**Common issues**:
- Missing environment variables
- Network connection lost
- API key invalid
- Port already in use

**Fix**: Restart the agent after fixing the issue

---

## Quick Start Summary

### For Testing (Local)

```bash
# Terminal 1
cd uagents_deploy
export ANTHROPIC_API_KEY=your_key
python3 standalone_compression_agent.py

# Terminal 2
cd uagents_deploy
export ANTHROPIC_API_KEY=your_key
python3 standalone_decision_agent.py

# Terminal 3
cd uagents_deploy
export KALSHI_EMAIL=your_email
export KALSHI_PASSWORD=your_password
export KALSHI_USE_DEMO=true
python3 standalone_kalshi_agent.py
```

**Copy the addresses** from startup logs!

### For Production (Cloud Server)

```bash
# SSH to server
ssh user@server

# Clone and setup
git clone <your-repo>
cd <your-repo>/uagents_deploy
pip3 install uagents anthropic requests

# Set env vars
export ANTHROPIC_API_KEY=...
export KALSHI_EMAIL=...
export KALSHI_PASSWORD=...

# Run in background
nohup python3 standalone_compression_agent.py > compression.log 2>&1 &
nohup python3 standalone_decision_agent.py > decision.log 2>&1 &
nohup python3 standalone_kalshi_agent.py > kalshi.log 2>&1 &

# Check logs
tail -f compression.log
```

---

## Comparison: Local vs Hosted

| Aspect | Local/Server Deployment | Agentverse Hosted |
|--------|------------------------|-------------------|
| **Setup** | Run Python script | Upload code via UI |
| **Cost** | Your server costs | Agentverse hosting fees |
| **Control** | Full control | Limited |
| **Dependencies** | You manage | Agentverse manages |
| **Scalability** | You scale | Auto-scaled |
| **Best For** | Hackathon, custom setup | Production, simplicity |

For your hackathon project, **local/server deployment is perfect** - you have full control and can iterate quickly!

---

## Final Checklist

- [x] All three agents have ASI:One support
- [x] `mailbox=True` set (enables Agentverse mailbox)
- [x] `publish_agent_details=True` set (enables registration)
- [x] Chat protocol included with `publish_manifest=True`
- [ ] Environment variables set
- [ ] Scripts running (locally or on server)
- [ ] Agent addresses copied from logs
- [ ] Tested on DeltaV

**You're ready to go!** Just run the scripts and they'll auto-register with Agentverse. 🚀

---

## Next Steps

1. **Run all three agents** (locally or on server)
2. **Copy agent addresses** from startup logs
3. **Test on DeltaV** by searching for your agents
4. **Create orchestrator** (optional) to chain agents together
5. **Deploy to production** when ready for 24/7 operation

No UI upload needed - your agents are already configured correctly! ✅
