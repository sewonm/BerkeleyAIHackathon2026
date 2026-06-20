"""Evidence chunk schema"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    """A single piece of evidence collected by a research agent"""

    source_type: Literal[
        "culture_web",
        "sports_video",
        "politics_news",
        "financial_research",
        "market",
        "manual"
    ] = Field(..., description="Type of evidence source")

    text: str = Field(..., description="The evidence text content")

    source_url: Optional[str] = Field(None, description="URL of the source if available")

    timestamp: Optional[str] = Field(None, description="Timestamp of evidence collection")

    confidence: Optional[float] = Field(None, description="Confidence score of the evidence")

    metadata: dict = Field(default_factory=dict, description="Additional metadata about the evidence")

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "culture_web",
                "text": "Movie X received 12 major nominations including Best Picture",
                "source_url": "https://example.com/awards-news",
                "timestamp": "2026-01-15T10:30:00Z",
                "confidence": 0.9,
                "metadata": {"author": "Awards Insider", "publication": "Entertainment Weekly"}
            }
        }
