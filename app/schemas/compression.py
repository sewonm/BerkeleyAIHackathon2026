"""Compression result schema"""

from pydantic import BaseModel, Field


class CompressionResult(BaseModel):
    """Result of compressing evidence chunks"""

    raw_token_count: int = Field(..., description="Number of tokens before compression")

    compressed_token_count: int = Field(..., description="Number of tokens after compression")

    compression_ratio: float = Field(..., description="Ratio of raw to compressed tokens")

    compressed_context: str = Field(..., description="The compressed context text")

    kept_chunks: list[dict] = Field(
        default_factory=list,
        description="Chunks that were kept with their scores"
    )

    dropped_chunks: list[dict] = Field(
        default_factory=list,
        description="Chunks that were dropped with their scores"
    )

    protected_terms: list[str] = Field(
        default_factory=list,
        description="Protected terms used during compression"
    )

    cache_hit: bool = Field(
        default=False,
        description="True if this result was served from Redis cache"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "raw_token_count": 18420,
                "compressed_token_count": 2130,
                "compression_ratio": 8.65,
                "compressed_context": "Movie X received 12 major nominations...",
                "kept_chunks": [
                    {"text": "Movie X received 12 major nominations", "score": 0.92}
                ],
                "dropped_chunks": [
                    {"text": "The weather was nice today", "score": 0.12}
                ],
                "protected_terms": ["Movie X", "Best Picture", "nomination"]
            }
        }
