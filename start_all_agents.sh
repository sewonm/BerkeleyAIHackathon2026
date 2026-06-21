#!/bin/bash
#
# start_all_agents.sh — launch the full Quorum multi-agent pipeline locally.
#
# Starts every agent the orchestrator is wired to (protocol-compatible variants only):
#   orchestrator        :8000   front door (chat + routing)
#   culture_web         :8001   evidence (culture)        handles EvidenceRequest
#   compression         :8002   compression_agent.py      handles CompressionRequest  (shared protocol)
#   decision            :8003   decision_agent.py         handles DecisionRequest     (shared protocol)
#   sports_video        :8004   evidence (sports)         handles EvidenceRequest
#   financial_research  :8006   evidence (financial)      handles EvidenceRequest
#
# NOT started (see notes at bottom):
#   - standalone_kalshi_agent.py  : port 8004 conflicts with sports + not protocol-wired yet
#   - standalone_*/graph_*        : incompatible message schemas (would silently drop messages)
#
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="$ROOT/uagents_deploy"
LOGDIR="$ROOT/logs"
PIDFILE="$ROOT/.agent_pids"
# Interpreter that actually has the deps installed (no venv in this repo).
PYTHON="${PYTHON:-/opt/miniconda3/bin/python}"

mkdir -p "$LOGDIR"
: > "$PIDFILE"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python interpreter not found at '$PYTHON'."
    echo "       Set PYTHON=/path/to/python and re-run."
    exit 1
fi

# Put the repo ROOT on PYTHONPATH so agents launched from uagents_deploy/ can
# import the repo-root `app` package. Without this, router's guarded
# `from app.services.llm_service import LLMService` fails silently, the LLM
# routing tier is disabled, and keyword-less questions route to "none".
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Export every var from .env so EVERY child agent sees keys + addresses
# (only orchestrator/sports call load_dotenv themselves; this covers the rest).
if [ -f "$ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ROOT/.env"
    set +a
    echo "✓ Loaded environment from .env"
else
    echo "⚠ No .env found at $ROOT/.env — agents will use built-in defaults"
fi

echo ""
echo "Cleaning up anything already on ports 8000-8006..."
for port in 8000 8001 8002 8003 8004 8006; do
    lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
done

cd "$DEPLOY" || exit 1

# start <label> <port> <script>
start() {
    local label="$1" port="$2" script="$3"
    echo "Starting $label on port $port ($script)..."
    nohup "$PYTHON" "$script" > "$LOGDIR/$label.log" 2>&1 &
    local pid=$!
    echo "$pid $label $port" >> "$PIDFILE"
    echo "  → PID $pid · log: logs/$label.log"
    sleep 2
}

echo ""
echo "=== Starting agents ==="
start compression       8002 compression_agent.py
start decision          8003 decision_agent.py
start culture_web       8001 culture_web_agent.py
start sports_video      8004 sports_video_agent.py
start financial_research 8006 financial_research_agent.py
# Orchestrator last, so downstream agents are already listening.
start orchestrator      8000 orchestrator_agent.py

echo ""
echo "=== All agents started ==="
echo ""
echo "Tail everything:   tail -f logs/*.log"
echo "Tail one agent:    tail -f logs/orchestrator.log"
echo "Stop everything:   ./stop_all_agents.sh"
echo ""
echo "Note: Kalshi trade-execution agent is NOT started — it collides with"
echo "      sports on port 8004 and isn't protocol-wired (ExecuteTradeRequest"
echo "      missing). Read-only analysis pipeline runs fully without it."
