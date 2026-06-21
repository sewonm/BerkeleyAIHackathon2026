"""
Agent configuration for Agentverse deployment.

This file contains the addresses and configuration for all agents in the system.
When deploying to Agentverse, update these addresses with the actual deployed agent addresses.
"""

import os
from typing import Dict

# Agent addresses - Update these after deploying to Agentverse
# Format: "agent_<id>...@agentverse.ai"
AGENT_ADDRESSES: Dict[str, str] = {
    # Core functional agents
    "culture_web_agent": os.getenv("CULTURE_WEB_AGENT_ADDRESS", ""),
    "compression_agent": os.getenv("COMPRESSION_AGENT_ADDRESS", ""),
    "decision_agent": os.getenv("DECISION_AGENT_ADDRESS", ""),

    # Orchestrator (user-facing)
    "orchestrator_agent": os.getenv("ORCHESTRATOR_AGENT_ADDRESS", ""),

    # Future agents (placeholders)
    "sports_video_agent": os.getenv("SPORTS_VIDEO_AGENT_ADDRESS", ""),
    "politics_news_agent": os.getenv("POLITICS_NEWS_AGENT_ADDRESS", ""),
    "financial_research_agent": os.getenv("FINANCIAL_RESEARCH_AGENT_ADDRESS", ""),
    "market_agent": os.getenv("MARKET_AGENT_ADDRESS", ""),
}

# Agent metadata for reference
AGENT_METADATA = {
    "culture_web_agent": {
        "name": "Culture Web Evidence Agent",
        "description": "Collects evidence from culture/entertainment web sources",
        "status": "IMPLEMENTED",
        "port": 8001,
    },
    "compression_agent": {
        "name": "Context Compression Agent",
        "description": "Compresses raw evidence into compact decision-ready context",
        "status": "IMPLEMENTED",
        "port": 8002,
    },
    "decision_agent": {
        "name": "Trading Decision Agent",
        "description": "Makes YES/NO/HOLD recommendations based on compressed evidence",
        "status": "IMPLEMENTED",
        "port": 8003,
    },
    "orchestrator_agent": {
        "name": "Orchestrator Agent (User-Facing)",
        "description": "Coordinates the multi-agent pipeline and provides user interface",
        "status": "IMPLEMENTED",
        "port": 8000,
    },
    "sports_video_agent": {
        "name": "Quorum Sports Evidence Agent",
        "description": "Live sport-agnostic evidence bundle (ESPN anchor + Browserbase noisy) for a Kalshi sports market",
        "status": "IMPLEMENTED",
        "port": 8004,
    },
    "politics_news_agent": {
        "name": "Politics News Evidence Agent",
        "description": "Collects evidence from political news sources",
        "status": "PLACEHOLDER",
        "port": 8005,
    },
    "financial_research_agent": {
        "name": "Financial Research Agent",
        "description": "Collects evidence from financial and economic sources",
        "status": "PLACEHOLDER",
        "port": 8006,
    },
    "market_agent": {
        "name": "Market Data Agent",
        "description": "Collects Kalshi market data and price information",
        "status": "PLACEHOLDER",
        "port": 8007,
    },
}


def get_agent_address(agent_name: str) -> str:
    """
    Get the address of an agent by name.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent address string, or empty string if not configured
    """
    return AGENT_ADDRESSES.get(agent_name, "")


def is_agent_implemented(agent_name: str) -> bool:
    """
    Check if an agent is implemented or just a placeholder.

    Args:
        agent_name: Name of the agent

    Returns:
        True if implemented, False if placeholder
    """
    metadata = AGENT_METADATA.get(agent_name, {})
    return metadata.get("status") == "IMPLEMENTED"


def get_all_implemented_agents() -> Dict[str, str]:
    """
    Get all implemented agent addresses.

    Returns:
        Dictionary of agent_name -> address for implemented agents only
    """
    return {
        name: addr
        for name, addr in AGENT_ADDRESSES.items()
        if is_agent_implemented(name) and addr
    }


def print_agent_status():
    """Print the status of all agents"""
    print("\n=== Agent Status ===\n")

    for agent_name, metadata in AGENT_METADATA.items():
        status = metadata["status"]
        address = AGENT_ADDRESSES.get(agent_name, "NOT CONFIGURED")

        status_emoji = "✅" if status == "IMPLEMENTED" else "📋"
        print(f"{status_emoji} {metadata['name']}")
        print(f"   Status: {status}")
        print(f"   Port: {metadata['port']}")
        print(f"   Address: {address if address else 'Not deployed'}")
        print()


if __name__ == "__main__":
    print_agent_status()
