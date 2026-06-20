"""Market data agent - PLACEHOLDER for future implementation"""

from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk


class MarketAgent(BaseAgent):
    """
    Agent that collects market data from Kalshi.

    TODO: Implement using Kalshi API
    TODO: Collect evidence from:
    - Current YES/NO prices
    - Order book data
    - Price movements
    - Volume metrics
    - Liquidity indicators
    - Implied probabilities
    - Historical price trends

    For MVP, this agent is a placeholder and returns empty results.
    """

    def __init__(self):
        super().__init__(
            name="MarketAgent",
            description="Collects market data from Kalshi (NOT IMPLEMENTED)"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Placeholder implementation - returns empty list.

        Args:
            market: The market to research

        Returns:
            Empty list (not implemented yet)
        """
        # TODO: Implement Kalshi market data collection
        print(f"[{self.name}] Skipping - not implemented in MVP")
        return []
