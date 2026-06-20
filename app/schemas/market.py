"""Market schema"""

from typing import Optional
from pydantic import BaseModel, Field


class Market(BaseModel):
    """A prediction market to research and analyze"""

    market_id: str = Field(..., description="Unique market identifier")

    title: str = Field(..., description="Market title")

    question: str = Field(..., description="Market question")

    category: str = Field(..., description="Market category (e.g., culture, sports, politics)")

    current_yes_price: Optional[float] = Field(None, description="Current YES price (0-1)")

    current_no_price: Optional[float] = Field(None, description="Current NO price (0-1)")

    resolution_criteria: str = Field(..., description="How the market will be resolved")

    protected_terms: list[str] = Field(
        default_factory=list,
        description="Important terms that should be preserved in compression"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "market_id": "sample-culture-oscars",
                "title": "Will Movie X win Best Picture?",
                "question": "Will Movie X win Best Picture at the next major awards ceremony?",
                "category": "culture",
                "current_yes_price": 0.42,
                "current_no_price": 0.58,
                "resolution_criteria": "Market resolves YES if Movie X officially wins Best Picture at the specified awards ceremony.",
                "protected_terms": ["Movie X", "Best Picture", "awards ceremony", "nomination", "box office", "critics"]
            }
        }
