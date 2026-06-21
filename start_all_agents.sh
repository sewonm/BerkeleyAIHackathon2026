#!/bin/bash

# Start All Agents Script
# This script starts all three agents in the background

cd "$(dirname "$0")/uagents_deploy"

# Activate virtual environment
source ../venv/bin/activate

# Kill any existing agents on these ports
echo "Cleaning up existing agents..."
lsof -ti:8002 | xargs kill -9 2>/dev/null || true
lsof -ti:8003 | xargs kill -9 2>/dev/null || true
lsof -ti:8004 | xargs kill -9 2>/dev/null || true

# Start Compression Agent
echo "Starting Compression Agent on port 8002..."
nohup python3 standalone_compression_agent.py > ../logs/compression.log 2>&1 &
COMPRESSION_PID=$!
echo "Compression Agent PID: $COMPRESSION_PID"

# Wait a bit
sleep 2

# Start Decision Agent
echo "Starting Decision Agent on port 8003..."
nohup python3 standalone_decision_agent.py > ../logs/decision.log 2>&1 &
DECISION_PID=$!
echo "Decision Agent PID: $DECISION_PID"

# Wait a bit
sleep 2

# Start Kalshi Agent
echo "Starting Kalshi Agent on port 8004..."
nohup python3 standalone_kalshi_agent.py > ../logs/kalshi.log 2>&1 &
KALSHI_PID=$!
echo "Kalshi Agent PID: $KALSHI_PID"

echo ""
echo "All agents started!"
echo ""
echo "To view logs:"
echo "  Compression: tail -f logs/compression.log"
echo "  Decision:    tail -f logs/decision.log"
echo "  Kalshi:      tail -f logs/kalshi.log"
echo ""
echo "To stop all agents:"
echo "  kill $COMPRESSION_PID $DECISION_PID $KALSHI_PID"
echo ""
echo "Or run: ./stop_all_agents.sh"
