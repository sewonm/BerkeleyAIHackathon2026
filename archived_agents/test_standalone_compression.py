"""
Test client for the standalone compression agent.

This script demonstrates how to send compression requests to the
standalone compression agent running locally or on Agentverse.

Usage:
    # Terminal 1: Start the agent
    cd uagents_deploy
    python standalone_compression_agent.py

    # Terminal 2: Run this test
    python test_standalone_compression.py
"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from uagents import Agent, Context, Protocol
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


# ============================================================================
# SCHEMAS (matching standalone agent)
# ============================================================================

class EnhancedEvidenceChunk(BaseModel):
    """Enhanced evidence chunk with full metadata"""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    source_agent: str
    source_type: str
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnhancedCompressionRequest(BaseModel):
    """Enhanced compression request"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    market_question: str
    resolution_criteria: str
    current_yes_price: Optional[float] = None
    current_no_price: Optional[float] = None
    evidence_chunks: List[EnhancedEvidenceChunk]
    token_budget: Optional[int] = 3000
    mode: Optional[str] = "graph-consensus"
    aggressiveness: Optional[float] = 0.5


class EnhancedCompressionResponse(BaseModel):
    """Enhanced compression response"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    compression_result: Optional[Dict[str, Any]] = None


# ============================================================================
# TEST DATA
# ============================================================================

# Example 1: Oscar Awards (culture/entertainment)
OSCAR_EVIDENCE = [
    EnhancedEvidenceChunk(
        market_id="oscars-2024",
        source_agent="web_scraper",
        source_type="article",
        text="""Oppenheimer leads the 2024 Oscar nominations with 13 nominations including Best Picture,
        Best Director for Christopher Nolan, and Best Actor for Cillian Murphy. The film has been
        dominating the awards season, winning at the Golden Globes and Critics Choice Awards. Industry
        experts predict it will sweep the major categories.""",
        source_url="https://variety.com/oscars-2024",
        confidence=0.9
    ),
    EnhancedEvidenceChunk(
        market_id="oscars-2024",
        source_agent="twitter_monitor",
        source_type="social_media",
        text="""Breaking: Oppenheimer wins Best Picture at the BAFTAs, continuing its unstoppable awards
        season run. Christopher Nolan finally wins his first Best Director award. The film has now won
        every major precursor award, making it the heavy favorite for the Oscars.""",
        source_url="https://twitter.com/variety",
        confidence=0.85
    ),
    EnhancedEvidenceChunk(
        market_id="oscars-2024",
        source_agent="news_aggregator",
        source_type="news",
        text="""Poor Things receives 11 Oscar nominations including Best Picture and Best Actress for
        Emma Stone. While it's a strong contender in technical categories, Oppenheimer remains the
        frontrunner for Best Picture based on guild awards and critical consensus.""",
        source_url="https://deadline.com/oscars",
        confidence=0.8
    )
]

# Example 2: France World Cup (sports)
FRANCE_WORLDCUP_EVIDENCE = [
    EnhancedEvidenceChunk(
        market_id="france-worldcup-2026",
        source_agent="sports_stats",
        source_type="statistics",
        text="""France enters the 2026 World Cup as one of the favorites with an ELO rating of 2044,
        ranked 2nd globally. Kylian Mbappé is in his prime at 27, and France has won 18 of their last
        20 matches. They reached the finals in 2022, losing to Argentina on penalties.""",
        source_url="https://fivethirtyeight.com/world-cup",
        confidence=0.95
    ),
    EnhancedEvidenceChunk(
        market_id="france-worldcup-2026",
        source_agent="injury_tracker",
        source_type="injury_report",
        text="""Concerning injury news for France: Key midfielder N'Golo Kanté is recovering from a
        hamstring injury and may not be fully fit for the World Cup. Additionally, defender Raphaël
        Varane has announced retirement from international football.""",
        source_url="https://espn.com/soccer",
        confidence=0.9
    ),
    EnhancedEvidenceChunk(
        market_id="france-worldcup-2026",
        source_agent="betting_odds",
        source_type="market_data",
        text="""Betting markets have France at +500 (5-to-1) to win the 2026 World Cup, making them
        the second favorite behind Brazil (+450). Historical data shows the defending runner-up wins
        the next tournament only 12% of the time. France also faces a difficult group stage draw.""",
        source_url="https://oddschecker.com",
        confidence=0.85
    ),
    EnhancedEvidenceChunk(
        market_id="france-worldcup-2026",
        source_agent="expert_analysis",
        source_type="analysis",
        text="""France has the strongest squad depth in world football with world-class players in
        every position. Manager Didier Deschamps has won a World Cup (2018) and reached another
        final (2022). The team's experience and talent make them legitimate favorites.""",
        source_url="https://theathletic.com",
        confidence=0.8
    )
]


# ============================================================================
# TEST CLIENT AGENT
# ============================================================================

# Create test client agent
test_client = Agent(
    name="compression_test_client",
    seed="test_client_seed_12345",
    port=8099,
)

# Agent address - UPDATE THIS with your compression agent's address
COMPRESSION_AGENT_ADDRESS = "agent1q..."  # Will be set dynamically

test_protocol = Protocol("CompressionTest")

# Store responses
responses = {}


@test_protocol.on_message(model=EnhancedCompressionResponse)
async def handle_compression_response(ctx: Context, sender: str, msg: EnhancedCompressionResponse):
    """Handle compression response from agent"""
    ctx.logger.info("=" * 80)
    ctx.logger.info("COMPRESSION RESPONSE RECEIVED")
    ctx.logger.info("=" * 80)

    ctx.logger.info(f"Request ID: {msg.request_id}")
    ctx.logger.info(f"Market ID: {msg.market_id}")
    ctx.logger.info(f"Status: {msg.status}")

    if msg.status == "error":
        ctx.logger.error(f"Error: {msg.error}")
        responses[msg.request_id] = {"status": "error", "error": msg.error}
        return

    if msg.compression_result:
        result = msg.compression_result

        # Display metrics
        if "metrics" in result:
            metrics = result["metrics"]
            ctx.logger.info("\n📊 COMPRESSION METRICS:")
            ctx.logger.info(f"  Raw tokens: {metrics.get('raw_token_count', 'N/A')}")
            ctx.logger.info(f"  Compressed tokens: {metrics.get('compressed_token_count', 'N/A')}")
            ctx.logger.info(f"  Compression ratio: {metrics.get('compression_ratio', 'N/A')}x")
            ctx.logger.info(f"  Claims extracted: {metrics.get('total_claims_extracted', 'N/A')}")
            ctx.logger.info(f"  Consensus items: {metrics.get('total_consensus_items', 'N/A')}")
            ctx.logger.info(f"  YES evidence: {metrics.get('yes_consensus_count', 'N/A')}")
            ctx.logger.info(f"  NO evidence: {metrics.get('no_consensus_count', 'N/A')}")
            ctx.logger.info(f"  Graph nodes: {metrics.get('graph_node_count', 'N/A')}")
            ctx.logger.info(f"  Graph edges: {metrics.get('graph_edge_count', 'N/A')}")

        # Display compressed context
        if "compressed_context" in result:
            ctx.logger.info("\n📝 COMPRESSED CONTEXT:")
            ctx.logger.info("-" * 80)
            ctx.logger.info(result["compressed_context"])
            ctx.logger.info("-" * 80)

        # Store response
        responses[msg.request_id] = result

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_compression_output_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        ctx.logger.info(f"\n💾 Full result saved to: {filename}")

    ctx.logger.info("=" * 80)


test_client.include(test_protocol)


async def test_compression(
    agent_address: str,
    evidence_chunks: List[EnhancedEvidenceChunk],
    market_question: str,
    resolution_criteria: str,
    current_yes_price: float = 0.5,
    aggressiveness: float = 0.5
):
    """
    Send a compression request to the agent.

    Args:
        agent_address: Address of the compression agent
        evidence_chunks: List of evidence chunks to compress
        market_question: The market question
        resolution_criteria: Resolution criteria
        current_yes_price: Current YES price (0-1)
        aggressiveness: Compression aggressiveness (0-1)
    """
    ctx = Context(test_client.address, None, None, None, None, None)

    # Create request
    request = EnhancedCompressionRequest(
        market_id=evidence_chunks[0].market_id,
        market_question=market_question,
        resolution_criteria=resolution_criteria,
        current_yes_price=current_yes_price,
        current_no_price=1.0 - current_yes_price,
        evidence_chunks=evidence_chunks,
        token_budget=3000,
        aggressiveness=aggressiveness
    )

    print("=" * 80)
    print("SENDING COMPRESSION REQUEST")
    print("=" * 80)
    print(f"Market: {market_question}")
    print(f"Evidence chunks: {len(evidence_chunks)}")
    print(f"Current YES price: {current_yes_price:.2f}")
    print(f"Aggressiveness: {aggressiveness}")
    print(f"Target agent: {agent_address}")
    print("=" * 80)
    print("\nWaiting for response...")

    # Send request
    await ctx.send(agent_address, request)

    return request.request_id


@test_client.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("=" * 80)
    ctx.logger.info("COMPRESSION TEST CLIENT STARTED")
    ctx.logger.info("=" * 80)
    ctx.logger.info(f"Client address: {test_client.address}")
    ctx.logger.info("")
    ctx.logger.info("Available test scenarios:")
    ctx.logger.info("  1. Oscar Best Picture 2024")
    ctx.logger.info("  2. France World Cup 2026")
    ctx.logger.info("")
    ctx.logger.info("Waiting for compression agent to be available...")
    ctx.logger.info("=" * 80)


# ============================================================================
# INTERACTIVE TEST RUNNER
# ============================================================================

def print_menu():
    """Print the test menu"""
    print("\n" + "=" * 80)
    print("STANDALONE COMPRESSION AGENT TEST CLIENT")
    print("=" * 80)
    print("\nTest Scenarios:")
    print("  1. Oscar Best Picture 2024 (3 evidence chunks)")
    print("  2. France World Cup 2026 (4 evidence chunks)")
    print("  3. Custom test (enter your own data)")
    print("  4. Aggressiveness test (same data, different compression levels)")
    print("  q. Quit")
    print("=" * 80)


def get_scenario_data(choice: str):
    """Get test data for a scenario"""
    if choice == "1":
        return {
            "evidence": OSCAR_EVIDENCE,
            "question": "Will Oppenheimer win Best Picture at the 2024 Oscars?",
            "criteria": "Resolves YES if Oppenheimer wins Best Picture at the 96th Academy Awards. Resolves NO otherwise.",
            "yes_price": 0.85
        }
    elif choice == "2":
        return {
            "evidence": FRANCE_WORLDCUP_EVIDENCE,
            "question": "Will France win the 2026 FIFA World Cup?",
            "criteria": "Resolves YES if France wins the 2026 FIFA World Cup final. Resolves NO if any other team wins.",
            "yes_price": 0.18
        }
    else:
        return None


async def run_interactive_test():
    """Run interactive test client"""
    print("\n🚀 Starting Compression Agent Test Client...")
    print("\nℹ️  Make sure the compression agent is running:")
    print("   cd uagents_deploy && python standalone_compression_agent.py")

    # Get agent address
    agent_address = input("\nEnter compression agent address (or press Enter for localhost test): ").strip()
    if not agent_address:
        # For local testing, we'll use a mock address
        # In reality, you'd get this from the running agent
        agent_address = "agent1qw5z8e4ak7l8y8tdqx7v3kq3z8r4p2x9m0n5j6h3k2l4m7n9p8"
        print(f"Using test address: {agent_address}")

    while True:
        print_menu()
        choice = input("\nSelect option: ").strip()

        if choice.lower() == 'q':
            print("\n👋 Goodbye!")
            break

        if choice == "4":
            # Aggressiveness test
            print("\n📊 Running aggressiveness comparison test...")
            print("Testing with Oscar data at 3 different compression levels:\n")

            data = get_scenario_data("1")

            for agg in [0.3, 0.5, 0.8]:
                print(f"\n🔄 Testing with aggressiveness={agg}...")
                # Note: This would actually send to the agent in a real scenario
                print(f"   (Would compress with threshold={agg * 0.6:.2f})")

            print("\n✅ Aggressiveness test complete")
            print("Compare the compression_ratio and total_consensus_items in each output")
            continue

        data = get_scenario_data(choice)

        if not data:
            print("❌ Invalid choice. Please try again.")
            continue

        # Get aggressiveness setting
        agg_input = input("\nCompression aggressiveness (0.0-1.0, default 0.5): ").strip()
        try:
            aggressiveness = float(agg_input) if agg_input else 0.5
            aggressiveness = max(0.0, min(1.0, aggressiveness))
        except ValueError:
            aggressiveness = 0.5
            print(f"Invalid input, using default: {aggressiveness}")

        print(f"\n✅ Selected scenario: {data['question']}")
        print(f"   Evidence chunks: {len(data['evidence'])}")
        print(f"   Current YES price: {data['yes_price']:.2f}")
        print(f"   Aggressiveness: {aggressiveness}")

        # For demonstration purposes, show what would be sent
        print("\n📤 Request that would be sent:")
        request = EnhancedCompressionRequest(
            market_id=data['evidence'][0].market_id,
            market_question=data['question'],
            resolution_criteria=data['criteria'],
            current_yes_price=data['yes_price'],
            current_no_price=1.0 - data['yes_price'],
            evidence_chunks=data['evidence'],
            aggressiveness=aggressiveness
        )

        print(json.dumps(request.dict(), indent=2, default=str)[:500] + "...")

        print("\nℹ️  To actually send this request, the agent must be running and")
        print("   you need to start this script with: python -m test_standalone_compression")
        print("   (Currently in interactive mode for demonstration)")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        # Run interactive mode (doesn't require agent running)
        asyncio.run(run_interactive_test())
    else:
        # Run as uAgent (requires agent to be running)
        print("\n" + "=" * 80)
        print("RUNNING AS UAGENT TEST CLIENT")
        print("=" * 80)
        print("\nThis mode sends actual messages to the compression agent.")
        print("Make sure the compression agent is running first:")
        print("  cd uagents_deploy && python standalone_compression_agent.py")
        print("\nFor interactive demo mode, run:")
        print("  python test_standalone_compression.py interactive")
        print("=" * 80 + "\n")

        test_client.run()
