#!/bin/bash

# Decision Agent Startup Script
# Run from project root: ./run_decision_agent.sh

cd "$(dirname "$0")"

echo "=== Starting Decision Agent ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Create it with: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if uagents is installed
if ! python3 -c "import uagents" 2>/dev/null; then
    echo "❌ uagents not installed in virtual environment!"
    echo "Install with: pip install uagents"
    exit 1
fi

# Check if uagents_core is installed (for chat protocol)
if ! python3 -c "import uagents_core" 2>/dev/null; then
    echo "⚠️  uagents_core not installed - chat protocol may not work"
    echo "Install with: pip install uagents-core"
    echo ""
fi

echo "✓ Virtual environment activated"
echo ""

# Run the agent
echo "Starting decision agent..."
echo ""
python3 uagents_deploy/standalone_decision_agent.py
