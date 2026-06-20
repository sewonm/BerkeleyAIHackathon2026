"""Sports/video research agent - PLACEHOLDER for future implementation"""

from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk


class SportsVideoAgent(BaseAgent):
    """
    Agent that analyzes sports video content and transcripts.

    TODO: Implement video analysis using Browserbase or video API
    TODO: Extract evidence from:
    - Game footage
    - Press conferences
    - Injury reports
    - Analyst commentary
    - Performance metrics
    - Lineup announcements

    For MVP, this agent is a placeholder and returns empty results.
    """

    def __init__(self):
        super().__init__(
            name="SportsVideoAgent",
            description="Analyzes sports video content and transcripts (NOT IMPLEMENTED)"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Placeholder implementation - returns empty list.

        Args:
            market: The market to research

        Returns:
            Empty list (not implemented yet)
        """
        # TODO: Implement sports video analysis
        print(f"[{self.name}] Skipping - not implemented in MVP")
        return []
