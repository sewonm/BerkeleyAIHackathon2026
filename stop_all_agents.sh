#!/bin/bash
#
# stop_all_agents.sh — stop every agent started by start_all_agents.sh.
#
ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$ROOT/.agent_pids"

echo "Stopping all agents..."

# Prefer killing the exact PIDs we recorded, then sweep the ports as a backstop.
if [ -f "$PIDFILE" ]; then
    while read -r pid label port; do
        [ -z "$pid" ] && continue
        kill -9 "$pid" 2>/dev/null && echo "✓ Stopped $label (PID $pid, port $port)" \
            || echo "  $label (PID $pid) not running"
    done < "$PIDFILE"
    rm -f "$PIDFILE"
fi

# Backstop: clear any stragglers still holding the pipeline ports.
for port in 8000 8001 8002 8003 8004 8006; do
    lsof -ti:"$port" | xargs kill -9 2>/dev/null \
        && echo "✓ Cleared port $port" || true
done

echo ""
echo "All agents stopped."
