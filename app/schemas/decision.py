"""Decision schema"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Decision(BaseModel):
    """Decision output from the decision agent"""

    recommendation: Literal["YES", "NO", "HOLD"] = Field(
        ...,
        description="Trading recommendation"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the recommendation (0-1)"
    )

    fair_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Estimated fair probability of YES outcome (0-1)"
    )

    reasoning: str = Field(..., description="Explanation of the decision")

    key_evidence: list[str] = Field(
        default_factory=list,
        description="Key pieces of evidence that informed the decision"
    )

    missing_info: list[str] = Field(
        default_factory=list,
        description="Information that would improve the decision if available"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recommendation": "YES",
                "confidence": 0.76,
                "fair_probability": 0.55,
                "reasoning": "Strong nominations and critical acclaim suggest Movie X has a good chance",
                "key_evidence": [
                    "Movie X received 12 major nominations",
                    "Critics ranked it among top contenders"
                ],
                "missing_info": [
                    "Final guild award results",
                    "Updated market movement"
                ]
            }
        }
