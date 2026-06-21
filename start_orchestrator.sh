#!/bin/bash

# Start Orchestrator with All Agent Addresses
# This script sets environment variables and starts the orchestrator

cd "$(dirname "$0")/uagents_deploy"

# Kill existing orchestrator on port 8000
echo "Cleaning up existing orchestrator..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo ""
echo "=== Configuring Agent Addresses ==="
echo ""

# Financial Research Agent (your friend's deployed agent)
export FINANCIAL_RESEARCH_AGENT_ADDRESS="agent1qdmqlr480a8t98jnahglgtpjjt8xz3jyyas8aksu5vvpk3dmtwaek6su5y7"
echo "✓ Financial Research Agent: ${FINANCIAL_RESEARCH_AGENT_ADDRESS}"

# Sports Video Agent (your friend's deployed agent)
export SPORTS_VIDEO_AGENT_ADDRESS="agent1qtl44wzgnadkpqne0rdpz24w85ljknmfszh3k2ws5ttcp8nm7hvuum0gr2g"
echo "✓ Sports Video Agent: ${SPORTS_VIDEO_AGENT_ADDRESS}"

# Compression Agent (REQUIRED - you need to deploy this)
if [ -z "$COMPRESSION_AGENT_ADDRESS" ]; then
    echo "⚠ Compression Agent: NOT SET (pipeline will stall without this)"
    echo "  Deploy standalone_compression_agent.py and set COMPRESSION_AGENT_ADDRESS"
else
    export COMPRESSION_AGENT_ADDRESS="$COMPRESSION_AGENT_ADDRESS"
    echo "✓ Compression Agent: ${COMPRESSION_AGENT_ADDRESS}"
fi

# Decision Agent (REQUIRED - you need to deploy this)
if [ -z "$DECISION_AGENT_ADDRESS" ]; then
    echo "⚠ Decision Agent: NOT SET (pipeline will stall without this)"
    echo "  Deploy standalone_decision_agent.py and set DECISION_AGENT_ADDRESS"
else
    export DECISION_AGENT_ADDRESS="$DECISION_AGENT_ADDRESS"
    echo "✓ Decision Agent: ${DECISION_AGENT_ADDRESS}"
fi

# Kalshi Agent (REQUIRED for trade execution)
if [ -z "$KALSHI_AGENT_ADDRESS" ]; then
    echo "⚠ Kalshi Agent: NOT SET (trade execution disabled)"
    echo "  Deploy standalone_kalshi_agent.py and set KALSHI_AGENT_ADDRESS"
else
    export KALSHI_AGENT_ADDRESS="$KALSHI_AGENT_ADDRESS"
    echo "✓ Kalshi Agent: ${KALSHI_AGENT_ADDRESS}"
fi

# Culture Web Agent (OPTIONAL)
if [ -z "$CULTURE_WEB_AGENT_ADDRESS" ]; then
    echo "ℹ Culture Web Agent: NOT SET (optional)"
else
    export CULTURE_WEB_AGENT_ADDRESS="$CULTURE_WEB_AGENT_ADDRESS"
    echo "✓ Culture Web Agent: ${CULTURE_WEB_AGENT_ADDRESS}"
fi

echo ""
echo "=== Starting Orchestrator Agent ==="
echo ""

# Activate virtual environment if it exists
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Start orchestrator
echo ""
echo "Starting orchestrator_agent.py..."
echo "Press Ctrl+C to stop"
echo ""

python3 orchestrator_agent.py
