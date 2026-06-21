"""
Message protocols for agent-to-agent communication.

These message models define the data structures exchanged between agents.
Each agent uses these to communicate in a standardized way.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


# ============================================================================
# Market Request/Response Messages
# ============================================================================

class MarketRequest(BaseModel):
    """Request to analyze a prediction market"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    market_id: str
    market_title: str
    market_question: str
    category: str
    current_yes_price: Optional[float] = None
    current_no_price: Optional[float] = None
    resolution_criteria: str
    protected_terms: List[str] = Field(default_factory=list)


# ============================================================================
# Evidence Collection Messages
# ============================================================================

class EvidenceRequest(BaseModel):
    """Request for evidence collection"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    market_question: str
    market_id: Optional[str] = None
    category: str
    protected_terms: List[str] = Field(default_factory=list)


class EvidenceChunkMsg(BaseModel):
    """Single piece of evidence"""
    source_type: Literal[
        "culture_web",
        "sports_video",
        "politics_news",
        "financial_research",
        "market",
        "manual"
    ]
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: dict = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    """Response containing collected evidence"""
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID  # References the original request
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str
    evidence_chunks: List[EvidenceChunkMsg]
    total_chunks: int


# ============================================================================
# Compression Messages
# ============================================================================

class CompressionRequest(BaseModel):
    """Request to compress evidence"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    market_question: str
    protected_terms: List[str]
    evidence_chunks: List[EvidenceChunkMsg]
    token_budget: int = 3000


class CompressionResponse(BaseModel):
    """Response with compressed context"""
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    raw_token_count: int
    compressed_token_count: int
    compression_ratio: float
    compressed_context: str
    kept_chunks_count: int
    dropped_chunks_count: int
    protected_terms: List[str]


# ============================================================================
# Decision Messages
# ============================================================================

class DecisionRequest(BaseModel):
    """Request for trading decision"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    market_title: str
    market_question: str
    current_yes_price: Optional[float] = None
    compressed_context: str
    kept_chunks_count: int


class DecisionResponse(BaseModel):
    """Trading decision recommendation"""
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    recommendation: Literal["YES", "NO", "HOLD"]
    confidence: float
    fair_probability: Optional[float] = None
    reasoning: str
    key_evidence: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)


# ============================================================================
# Final Result Messages
# ============================================================================

class FinalAnalysisResult(BaseModel):
    """Complete analysis result from orchestrator"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    market_title: str

    # Compression metrics
    raw_token_count: int
    compressed_token_count: int
    compression_ratio: float

    # Decision
    recommendation: Literal["YES", "NO", "HOLD"]
    confidence: float
    fair_probability: Optional[float] = None
    reasoning: str
    key_evidence: List[str]
    missing_info: List[str]

    # Agent involvement
    agents_used: List[str]
    processing_time_seconds: float


# ============================================================================
# Status/Acknowledgement Messages
# ============================================================================

class AgentStatus(BaseModel):
    """Agent status update"""
    msg_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str
    status: Literal["ready", "processing", "completed", "error"]
    message: str


class Acknowledgement(BaseModel):
    """Simple acknowledgement message"""
    msg_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str
    acknowledged: bool = True
