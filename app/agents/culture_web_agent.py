"""Culture/web research agent - IMPLEMENTED for MVP"""

import os
from typing import List

from app.agents.base_agent import BaseAgent
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.utils.chunking import split_text_into_chunks


class CultureWebAgent(BaseAgent):
    """
    Agent that collects culture/entertainment evidence from web sources.

    For the MVP, this reads from a local sample file.
    In production, this would use Browserbase to browse live web sources.

    Domains:
    - Entertainment news
    - Box office data
    - Streaming metrics
    - Award announcements
    - Celebrity news
    - Music charts
    - Cultural trends
    - Viral content
    """

    def __init__(self):
        super().__init__(
            name="CultureWebAgent",
            description="Collects evidence from culture and entertainment web sources"
        )

    def run(self, market: Market) -> List[EvidenceChunk]:
        """
        Collect culture/web evidence for the market.

        For MVP, reads from examples/raw_context/culture_web_context.txt

        Args:
            market: The market to research

        Returns:
            List of evidence chunks from culture/web sources
        """
        # For MVP: read from local sample file
        sample_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "examples",
            "raw_context",
            "culture_web_context.txt"
        )

        if not os.path.exists(sample_file_path):
            print(f"Warning: Sample file not found at {sample_file_path}")
            return []

        with open(sample_file_path, 'r') as f:
            raw_text = f.read()

        # Split into chunks
        text_chunks = split_text_into_chunks(raw_text, max_words=120)

        # Convert to EvidenceChunk objects
        evidence_chunks = []
        for chunk_text in text_chunks:
            chunk = EvidenceChunk(
                source_type="culture_web",
                text=chunk_text,
                source_url="local://examples/raw_context/culture_web_context.txt",
                timestamp=None,
                confidence=0.8,  # Default confidence for local samples
                metadata={"agent": self.name, "is_sample_data": True}
            )
            evidence_chunks.append(chunk)

        print(f"[{self.name}] Collected {len(evidence_chunks)} evidence chunks")
        return evidence_chunks
