#!/bin/bash
#
# start_agents_windows.sh — launch each agent in its OWN macOS Terminal window,
# running in the foreground so you see its live output (great for demos).
#
# This is the visible-terminal alternative to start_all_agents.sh (which runs
# everything in the background and logs to logs/). Use ONE or the other — both
# bind the same ports.
#
#   Ctrl+C in a window stops that one agent. Close the window to kill it.
#
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-/opt/miniconda3/bin/python}"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python not found at '$PYTHON'. Set PYTHON=/path/to/python and re-run."
    exit 1
fi

echo "Cleaning up anything already on ports 8000-8006..."
for port in 8000 8001 8002 8003 8004 8006; do
    lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
done

# Open one Terminal.app window running <script> in the foreground, with the repo
# root on PYTHONPATH (so `app` imports -> LLM router tier active) and .env loaded.
open_window() {
    local label="$1" script="$2"
    local inner="cd '$ROOT' && set -a && source .env && set +a && export PYTHONPATH='$ROOT' && echo '===== $label =====' && '$PYTHON' uagents_deploy/$script"
    osascript -e "tell application \"Terminal\" to do script \"$inner\"" >/dev/null
    echo "  → opened window: $label ($script)"
    sleep 1
}

echo ""
echo "=== Opening a Terminal window per agent ==="
open_window compression        compression_agent.py
open_window decision           decision_agent.py
open_window culture_web        culture_web_agent.py
open_window sports_video       sports_video_agent.py
open_window financial_research financial_research_agent.py
open_window orchestrator       orchestrator_agent.py

osascript -e 'tell application "Terminal" to activate' >/dev/null

echo ""
echo "All agent windows opened. Each runs in its own Terminal window."
echo "Stop one: Ctrl+C in its window.  Stop all: ./stop_all_agents.sh"
