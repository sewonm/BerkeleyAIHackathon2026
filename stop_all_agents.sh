#!/bin/bash

# Stop All Agents Script

echo "Stopping all agents..."

# Kill agents by port
lsof -ti:8002 | xargs kill -9 2>/dev/null && echo "✓ Stopped Compression Agent (port 8002)" || echo "  Compression Agent not running"
lsof -ti:8003 | xargs kill -9 2>/dev/null && echo "✓ Stopped Decision Agent (port 8003)" || echo "  Decision Agent not running"
lsof -ti:8004 | xargs kill -9 2>/dev/null && echo "✓ Stopped Kalshi Agent (port 8004)" || echo "  Kalshi Agent not running"

echo ""
echo "All agents stopped!"
