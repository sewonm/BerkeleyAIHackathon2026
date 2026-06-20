"""Base agent class for all research agents"""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk


class BaseAgent(ABC):
    """
    Base class for all research agents.

    Each agent is responsible for collecting evidence from a specific domain
    (e.g., culture/web, sports/video, politics/news, financial, market data).
    """

    def __init__(self, name: str, description: str):
        """
        Initialize the base agent.

        Args:
            name: Agent name
            description: Description of what this agent does
        """
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Run the agent to collect evidence for a given market.

        Args:
            market: The market to research

        Returns:
            List of evidence chunks collected by this agent
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
