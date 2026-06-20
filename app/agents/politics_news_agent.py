"""Politics/news research agent - PLACEHOLDER for future implementation"""

from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk


class PoliticsNewsAgent(BaseAgent):
    """
    Agent that collects political and news-related evidence.

    TODO: Implement using Browserbase or news APIs
    TODO: Collect evidence from:
    - Breaking news
    - Polling data
    - Official announcements
    - Political statements
    - Court decisions
    - Regulatory updates
    - Event deadlines

    For MVP, this agent is a placeholder and returns empty results.
    """

    def __init__(self):
        super().__init__(
            name="PoliticsNewsAgent",
            description="Collects political and news evidence (NOT IMPLEMENTED)"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Placeholder implementation - returns empty list.

        Args:
            market: The market to research

        Returns:
            Empty list (not implemented yet)
        """
        # TODO: Implement politics/news research
        print(f"[{self.name}] Skipping - not implemented in MVP")
        return []
