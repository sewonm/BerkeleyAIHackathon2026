"""
Advanced schemas for graph-consensus compression.

These schemas support the sophisticated compression pipeline with:
- Claim extraction
- Evidence graphs
- Consensus clustering
- Information-value scoring
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


# ============================================================================
# Claim Models
# ============================================================================

class ExtractedClaim(BaseModel):
    """A structured claim extracted from raw evidence"""
    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    claim_text: str
    canonical_text: str  # Normalized form
    source_chunk_id: str
    source_agent: str

    # Extracted elements
    entities: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    numbers: List[str] = Field(default_factory=list)

    # Classification
    direction: Literal["YES", "NO", "NEUTRAL"] = "NEUTRAL"
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    market_impact_score: float = Field(0.0, ge=0.0, le=1.0)
    estimated_probability_shift: float = Field(0.0, ge=-1.0, le=1.0)

    # Metadata
    reason: Optional[str] = None
    extraction_method: Literal["claude", "heuristic"] = "heuristic"
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# Evidence Graph Models
# ============================================================================

class GraphNode(BaseModel):
    """A node in the evidence graph"""
    node_id: str
    node_type: Literal["market", "claim", "entity", "source", "event", "metric"]
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the evidence graph"""
    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    edge_type: Literal[
        "supports",
        "opposes",
        "mentions",
        "reported_by",
        "conflicts_with",
        "affects",
        "priced_in_by"
    ]
    source_node_id: str
    target_node_id: str
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraph(BaseModel):
    """Complete evidence graph"""
    graph_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

    def add_node(self, node: GraphNode):
        """Add a node to the graph"""
        self.nodes.append(node)

    def add_edge(self, edge: GraphEdge):
        """Add an edge to the graph"""
        self.edges.append(edge)

    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None


# ============================================================================
# Consensus Models
# ============================================================================

class ConsensusItem(BaseModel):
    """A consensus cluster of similar claims"""
    consensus_id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_claim: str
    direction: Literal["YES", "NO", "NEUTRAL"]

    # Source tracking
    source_count: int = 0
    source_agents: List[str] = Field(default_factory=list)
    source_diversity_score: float = 0.0

    # Agreement metrics
    agreement_level: Literal["high", "medium", "low"] = "medium"
    consensus_entropy: float = 0.0  # 0 = full agreement, higher = more disagreement

    # Scoring
    confidence: float = 0.5
    estimated_probability_shift: float = 0.0
    information_value: float = 0.0

    # Supporting data
    supporting_claim_ids: List[str] = Field(default_factory=list)
    opposing_claim_ids: List[str] = Field(default_factory=list)

    # Metadata
    entities: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    numbers: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsensusLedger(BaseModel):
    """Collection of consensus items"""
    ledger_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    consensus_items: List[ConsensusItem] = Field(default_factory=list)

    def add_item(self, item: ConsensusItem):
        """Add a consensus item"""
        self.consensus_items.append(item)

    def get_by_direction(self, direction: Literal["YES", "NO", "NEUTRAL"]) -> List[ConsensusItem]:
        """Get items by direction"""
        return [item for item in self.consensus_items if item.direction == direction]

    def get_top_by_value(self, n: int = 5, direction: Optional[str] = None) -> List[ConsensusItem]:
        """Get top N items by information value"""
        items = self.consensus_items
        if direction:
            items = self.get_by_direction(direction)
        return sorted(items, key=lambda x: x.information_value, reverse=True)[:n]


# ============================================================================
# Compression Result Models
# ============================================================================

class CompressionMetrics(BaseModel):
    """Metrics about the compression process"""
    raw_token_count: int
    compressed_token_count: int
    compression_ratio: float
    token_budget: int

    # Claim metrics
    total_claims_extracted: int = 0
    total_consensus_items: int = 0
    yes_consensus_count: int = 0
    no_consensus_count: int = 0
    neutral_consensus_count: int = 0

    # Graph metrics
    graph_node_count: int = 0
    graph_edge_count: int = 0

    # Processing metrics
    claude_calls: int = 0
    claude_failures: int = 0
    heuristic_fallbacks: int = 0
    redis_hits: int = 0
    redis_misses: int = 0


class AdvancedCompressionResult(BaseModel):
    """Complete result of the advanced compression pipeline"""
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    market_id: str

    # Core outputs
    evidence_graph: EvidenceGraph
    consensus_ledger: ConsensusLedger

    # Organized evidence
    top_supporting_evidence: List[ConsensusItem] = Field(default_factory=list)
    top_opposing_evidence: List[ConsensusItem] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)

    # Compressed output
    compressed_context: str

    # Metrics
    metrics: CompressionMetrics

    # Mode
    mode: str = "graph-consensus"

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# Request/Response for uAgent
# ============================================================================

class EnhancedEvidenceChunk(BaseModel):
    """Enhanced evidence chunk with full metadata"""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    source_agent: str
    source_type: str
    text: str
    source_url: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = 0.8
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnhancedCompressionRequest(BaseModel):
    """Enhanced compression request"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    market_question: str
    resolution_criteria: str
    current_yes_price: Optional[float] = None
    current_no_price: Optional[float] = None
    evidence_chunks: List[EnhancedEvidenceChunk]
    token_budget: Optional[int] = 3000
    mode: Optional[str] = "graph-consensus"


class EnhancedCompressionResponse(BaseModel):
    """Enhanced compression response"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    compression_result: Optional[AdvancedCompressionResult] = None
