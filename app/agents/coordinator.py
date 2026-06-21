"""Coordinator that orchestrates the multi-agent research pipeline"""

from typing import Dict, Any

from app.agents.culture_web_agent import CultureWebAgent
from app.agents.sports_video_agent import SportsVideoAgent
from app.agents.politics_news_agent import PoliticsNewsAgent
from app.agents.financial_research_agent import FinancialResearchAgent
from app.agents.market_agent import MarketAgent
from app.agents.decision_agent import DecisionAgent
from app.compression.unified_compressor import UnifiedCompressor
from app.schemas.market import Market
from app.schemas.decision import Decision
from app.schemas.compression import CompressionResult


class Coordinator:
    """
    Coordinates the multi-agent research pipeline.

    Flow:
    1. Run specialized research agents to collect evidence
    2. Pass evidence to compression layer
    3. Send compressed context to decision agent
    4. Return final decision and compression metrics

    For MVP, only CultureWebAgent is active.
    Other agents are initialized but return empty results.
    """

    def __init__(self, token_budget: int = 3000):
        """
        Initialize the coordinator with all agents.

        Args:
            token_budget: Maximum tokens for compressed context
        """
        self.token_budget = token_budget

        # Initialize all agents
        # For MVP, only CultureWebAgent is implemented
        self.culture_agent = CultureWebAgent()
        self.sports_agent = SportsVideoAgent()  # Placeholder
        self.politics_agent = PoliticsNewsAgent()  # Placeholder
        self.financial_agent = FinancialResearchAgent()  # Placeholder
        self.market_agent = MarketAgent()  # Placeholder

        # Initialize decision agent
        self.decision_agent = DecisionAgent()

        # Initialize compressor
        self.compressor = UnifiedCompressor()

    def run(self, market: Market) -> Dict[str, Any]:
        """
        Run the full research and decision pipeline.

        Args:
            market: The market to analyze

        Returns:
            Dictionary with compression result and decision
        """
        print(f"\n{'='*60}")
        print(f"COORDINATOR: Analyzing market '{market.title}'")
        print(f"{'='*60}\n")

        # Step 1: Collect evidence from agents
        print("STEP 1: Collecting evidence from agents...")
        all_evidence = []

        # For MVP: Only run CultureWebAgent
        # Other agents are called but return empty results
        all_evidence.extend(self.culture_agent.run(market))

        # Future agents (placeholders for now)
        all_evidence.extend(self.sports_agent.run(market))
        all_evidence.extend(self.politics_agent.run(market))
        all_evidence.extend(self.financial_agent.run(market))
        all_evidence.extend(self.market_agent.run(market))

        print(f"\nTotal evidence chunks collected: {len(all_evidence)}\n")

        # Step 2: Compress evidence
        print("STEP 2: Compressing evidence...")
        compression_result: CompressionResult = self.compressor.compress(
            market=market,
            evidence_chunks=all_evidence,
            token_budget=self.token_budget
        )

        print(f"Raw tokens: {compression_result.raw_token_count}")
        print(f"Compressed tokens: {compression_result.compressed_token_count}")
        print(f"Compression ratio: {compression_result.compression_ratio:.2f}x\n")

        # Step 3: Make decision
        print("STEP 3: Making decision...")
        decision: Decision = self.decision_agent.run(
            market=market,
            compressed_context=compression_result.compressed_context,
            kept_chunks=compression_result.kept_chunks
        )

        print(f"Recommendation: {decision.recommendation}")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"Fair probability: {decision.fair_probability}\n")

        # Return combined result
        return {
            "market": market,
            "compression": compression_result,
            "decision": decision
        }
