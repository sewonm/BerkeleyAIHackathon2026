"""Financial research agent - PLACEHOLDER for future implementation"""

from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk


class FinancialResearchAgent(BaseAgent):
    """
    Agent that analyzes financial and economic data.

    TODO: Implement using financial data APIs or Browserbase
    TODO: Collect evidence from:
    - Earnings reports
    - Economic indicators
    - Market movements
    - Fed statements
    - Analyst expectations
    - Inflation data
    - Company filings

    For MVP, this agent is a placeholder and returns empty results.
    """

    def __init__(self):
        super().__init__(
            name="FinancialResearchAgent",
            description="Analyzes financial and economic data (NOT IMPLEMENTED)"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Placeholder implementation - returns empty list.

        Args:
            market: The market to research

        Returns:
            Empty list (not implemented yet)
        """
        # TODO: Implement financial research
        print(f"[{self.name}] Skipping - not implemented in MVP")
        return []
