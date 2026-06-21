# How to Run the Agents

## Quick Start

### Compression Agent

From the project root directory:

```bash
./run_compression_agent.sh
```

Or manually:

```bash
# From project root
source venv/bin/activate
python3 uagents_deploy/standalone_compression_agent.py
```

### Decision Agent

From the project root directory:

```bash
./run_decision_agent.sh
```

Or manually:

```bash
# From project root
source venv/bin/activate
python3 uagents_deploy/standalone_decision_agent.py
```

### Sports Video Agent

```bash
# From project root
source venv/bin/activate
python3 uagents_deploy/sports_video_agent.py
```

### Orchestrator Agent

```bash
# From project root
./start_orchestrator.sh
```

---

## Common Issues

### Issue: `FileNotFoundError: [Errno 2] No such file or directory`

**Problem:** Running the agent from the wrong directory or without activating venv.

**Solution:**
```bash
# Make sure you're in the project root
cd /Users/sewonmyung/BerkeleyAIHackathon2026

# Activate virtual environment
source venv/bin/activate

# Then run the agent
python3 uagents_deploy/standalone_compression_agent.py
```

### Issue: `ModuleNotFoundError: No module named 'uagents'`

**Problem:** Virtual environment not activated or uagents not installed.

**Solution:**
```bash
# Activate venv
source venv/bin/activate

# Install uagents if needed
pip install uagents uagents-core
```

### Issue: `[Warning] Chat protocol not available`

**Problem:** `uagents_core` package not installed.

**Solution:**
```bash
source venv/bin/activate
pip install uagents-core
```

### Issue: `unrecognized schema digest` error

**Problem:** Chat protocol not properly configured.

**Solution:** Make sure you've applied the latest fixes:
- Correct imports from `uagents_core.contrib.protocols.chat`
- ChatAcknowledgement handler is present
- Protocol created with `Protocol(spec=chat_protocol_spec)`

See [CHAT_PROTOCOL_COMPLETE_FIX.md](CHAT_PROTOCOL_COMPLETE_FIX.md) for details.

---

## Testing After Starting

Once an agent starts successfully, you should see:

```
[agent_name] Agent started!
[agent_name] Address: agent1q...
[agent_name] Port: 8XXX

Agent address: agent1q...

Add this agent to Agentverse by visiting: https://agentverse.ai/agents/local/...
```

**Next steps:**

1. **Copy the Agentverse URL** from the terminal
2. **Open it in your browser**
3. **Click "Connect" → "Mailbox" → "Finish"**
4. **Go to the "Testing" tab → "Chat"**
5. **Type `demo`** to test the agent

Expected response:
- ✅ Demo output appears in chat
- ✅ No "unrecognized schema digest" errors in terminal
- ✅ Logs show `ACK from <address> for msg <id>`

---

## Running Multiple Agents

Each agent needs its own terminal window:

**Terminal 1:**
```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./run_compression_agent.sh
```

**Terminal 2:**
```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./run_decision_agent.sh
```

**Terminal 3:**
```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./start_orchestrator.sh
```

**Note:** Each agent runs on a different port:
- Compression: port 8001
- Decision: port 8002
- Sports Video: port 8004
- Orchestrator: port 8000

---

## Stopping Agents

**To stop an agent:**
- Press `Ctrl+C` in the terminal where it's running

**To kill a specific agent by port:**
```bash
# Kill agent on port 8001 (compression)
lsof -ti:8001 | xargs kill -9

# Kill agent on port 8002 (decision)
lsof -ti:8002 | xargs kill -9

# Kill all agents
lsof -ti:8000,8001,8002,8004 | xargs kill -9
```

---

## Directory Structure

Always run agents from the **project root**:

```
/Users/sewonmyung/BerkeleyAIHackathon2026/
├── venv/                           # Virtual environment (must activate)
├── uagents_deploy/
│   ├── standalone_compression_agent.py
│   ├── standalone_decision_agent.py
│   ├── sports_video_agent.py
│   └── orchestrator_agent.py
├── run_compression_agent.sh        # ← Use these scripts
├── run_decision_agent.sh
└── start_orchestrator.sh
```

**Always:**
1. `cd` to project root first
2. Run scripts from there
3. OR manually activate venv + run with full path

**Never:**
1. `cd` into `uagents_deploy/` and run directly
2. Run without activating venv
3. Run from a deleted or moved directory

---

## Full Testing Workflow

### 1. Test Compression Agent Alone

```bash
# Terminal 1
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./run_compression_agent.sh
```

- Copy Agentverse URL from output
- Open in browser → Connect → Mailbox
- Go to Chat tab
- Type: `demo`
- Expected: Compression demo output

### 2. Test Decision Agent Alone

```bash
# Terminal 2
cd /Users/sewonmyung/BerkeleyAIHackathon2026
./run_decision_agent.sh
```

- Copy Agentverse URL from output
- Open in browser → Connect → Mailbox
- Go to Chat tab
- Type: `demo`
- Expected: Decision demo output

### 3. Test Full Pipeline

Once compression and decision agents are running and deployed:

```bash
# Terminal 3
cd /Users/sewonmyung/BerkeleyAIHackathon2026

# Set agent addresses (get from running agents)
export COMPRESSION_AGENT_ADDRESS="agent1q..."
export DECISION_AGENT_ADDRESS="agent1q..."
export KALSHI_AGENT_ADDRESS="agent1q..."  # If you have it

# Start orchestrator
./start_orchestrator.sh
```

- Go to orchestrator Agentverse chat
- Type: `Will France win the World Cup 2026?`
- Expected: Full pipeline execution with decision + confirmation prompt

---

## Checklist Before Running

- [ ] In project root directory (`/Users/sewonmyung/BerkeleyAIHackathon2026`)
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] uagents installed (`pip install uagents uagents-core`)
- [ ] Port not already in use (`lsof -ti:8001` returns nothing)
- [ ] Network connectivity to agentverse.ai (for mailbox)

---

## Quick Reference

| Agent | Script | Port | Address Env Var |
|-------|--------|------|-----------------|
| Compression | `./run_compression_agent.sh` | 8001 | COMPRESSION_AGENT_ADDRESS |
| Decision | `./run_decision_agent.sh` | 8002 | DECISION_AGENT_ADDRESS |
| Sports Video | `python3 uagents_deploy/sports_video_agent.py` | 8004 | SPORTS_VIDEO_AGENT_ADDRESS |
| Financial Research | Already deployed | N/A | FINANCIAL_RESEARCH_AGENT_ADDRESS |
| Orchestrator | `./start_orchestrator.sh` | 8000 | N/A (this is the main agent) |
| Kalshi | `python3 uagents_deploy/standalone_kalshi_agent.py` | 8003 | KALSHI_AGENT_ADDRESS |

---

**Ready to test!** 🚀

Start with compression and decision agents individually, then move to the full pipeline once both are working.
