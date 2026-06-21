# Quick Start - Run Your Agents

All three agents have been updated with `agentverse={"use_mailbox": True}` to automatically handle mailbox creation.

---

## Step 1: Run the Compression Agent

```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026/uagents_deploy
source ../venv/bin/activate
python3 standalone_compression_agent.py
```

**What to check:**
- ✅ Look for: `Agent registration status updated to active`
- ✅ Look for: `Registration on Almanac API successful`
- ❌ Should NOT see: `Agent mailbox not found` (if you still see this, continue to Step 2)

**Copy the agent address** from the logs:
```
Address: agent1qfrrxh3yxjk39dvzpjape9q7n62832ydkgju4yxcm57u93f2rvpywvl7g9v
```

---

## Step 2: Check "My Agents" on Agentverse

While your agent is running:

1. **Go to**: https://agentverse.ai/
2. **Click**: "My Agents" in the left sidebar
3. **Look for**: Your agent with name `compression_agent_standalone`
4. **Click on it** to open details

### If you see a mailbox option:
- Click "Create Mailbox" or "Enable Mailbox"
- Restart your agent (Ctrl+C, then run again)

### If you DON'T see your agent yet:
- Wait 1-2 minutes for registration to sync
- Refresh the page
- The logs showed successful registration, so it should appear

---

## Step 3: Run Decision Agent (in new terminal)

```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026/uagents_deploy
source ../venv/bin/activate
python3 standalone_decision_agent.py
```

**Copy the agent address** from logs.

Repeat the mailbox check in "My Agents" if needed.

---

## Step 4: Run Kalshi Agent (in new terminal)

```bash
cd /Users/sewonmyung/BerkeleyAIHackathon2026/uagents_deploy
source ../venv/bin/activate

# Set Kalshi credentials
export KALSHI_EMAIL=your_email@example.com
export KALSHI_PASSWORD=your_password
export KALSHI_USE_DEMO=true

python3 standalone_kalshi_agent.py
```

**Copy the agent address** from logs.

---

## What the Mailbox Update Does

The `agentverse={"use_mailbox": True}` configuration explicitly tells each agent:
- Use Agentverse mailbox for remote messaging
- Automatically request mailbox creation
- Handle mailbox communication

This **should** automatically create the mailbox without manual intervention.

---

## Expected Logs (Success)

### Compression Agent:
```
INFO: [compression_agent_standalone]: Starting agent with address: agent1qfrrxh...
INFO: [compression_agent_standalone]: Starting server on http://0.0.0.0:8002
INFO: [compression_agent_standalone]: Starting mailbox client for https://agentverse.ai
INFO: [compression_agent_standalone]: Agent registration status updated to active
INFO: [compression_agent_standalone]: [compression_agent_standalone] Standalone Compression Agent started!
INFO: [compression_agent_standalone]: Address: agent1qfrrxh...
INFO: [compression_agent_standalone]: Custom protocol: ENABLED (agent-to-agent communication)
INFO: [compression_agent_standalone]: ASI:One chat protocol: DISABLED (install uagents.chat)
INFO: [uagents.registration]: Registration on Almanac API successful
```

**No "mailbox not found" warning!**

---

## Your Agent Addresses

After running all three, you'll have:

```python
COMPRESSION_AGENT = "agent1qfrrxh..."  # From compression agent logs
DECISION_AGENT = "agent1q..."          # From decision agent logs
KALSHI_AGENT = "agent1q..."            # From kalshi agent logs
```

**Save these!** You'll use them to send messages between agents.

---

## If You Still See Mailbox Warning

If after the update you still see `Agent mailbox not found`:

1. **Go to Agentverse "My Agents"**: https://agentverse.ai/
2. **Find your agent** (by name or address)
3. **Click on it** to open details
4. **Manually create mailbox** (there should be a button/toggle)
5. **Restart agent**

The manual UI method is the fallback if automatic creation doesn't work.

---

## Next Steps

Once all three agents are running **without mailbox warnings**:

### Test Agent-to-Agent Communication

Create a simple test to verify they can communicate:

```python
from uagents import Agent, Context

test_agent = Agent(name="test", seed="test123", port=9000)

COMPRESSION_AGENT = "agent1qfrrxh..."  # Your actual address

@test_agent.on_event("startup")
async def test_compression(ctx: Context):
    from standalone_compression_agent import EnhancedCompressionRequest

    request = EnhancedCompressionRequest(
        market_id="test",
        market_question="Test question?",
        evidence_chunks=[
            {"text": "Evidence 1", "source": "test"},
            {"text": "Evidence 2", "source": "test2"}
        ]
    )

    await ctx.send(COMPRESSION_AGENT, request)
    print(f"Sent test request to {COMPRESSION_AGENT}")

if __name__ == "__main__":
    test_agent.run()
```

### Build Your Hackathon Project

With all three agents running:
1. ✅ Compression Agent - Ready
2. ✅ Decision Agent - Ready
3. ✅ Kalshi Agent - Ready

You can now build your orchestrator or client application!

---

## Troubleshooting

### Issue: Still see "mailbox not found"
**Fix**: Go to "My Agents" on Agentverse and manually create mailbox

### Issue: Can't find agent in "My Agents"
**Fix**: Wait 2-3 minutes and refresh (registration takes time to sync)

### Issue: Agent crashes on startup
**Fix**: Check environment variables (ANTHROPIC_API_KEY, KALSHI credentials)

### Issue: Port already in use
**Fix**: Change port in agent code or kill existing process:
```bash
lsof -ti:8002 | xargs kill -9  # For compression agent
lsof -ti:8003 | xargs kill -9  # For decision agent
lsof -ti:8004 | xargs kill -9  # For kalshi agent
```

---

## Summary

✅ All three agents updated with `agentverse={"use_mailbox": True}`
✅ Run each agent in separate terminal
✅ Check "My Agents" on Agentverse to verify registration
✅ Create mailbox if needed (should be automatic now)
✅ Copy agent addresses for communication

You're ready to build your trading system! 🚀
