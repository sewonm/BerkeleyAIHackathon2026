"""
Self-contained Advanced Compression uAgent for Agentverse Deployment.

This file contains ALL compression logic in a single file for easy deployment.
No external dependencies on app/* modules - fully standalone.

Implements:
- Claim extraction (Claude or heuristic)
- Evidence graph construction
- Consensus clustering
- Information-value scoring
- Contradiction detection

ASI:One Compatible:
- Supports ChatMessage protocol for DeltaV/Agentverse interaction
- Supports custom protocol for agent-to-agent communication
"""

import re
import json
import os
import math
import traceback
from typing import List, Optional, Literal, Dict, Any, Tuple, Set
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field

from uagents import Agent, Context, Protocol

# ASI:One chat protocol imports
try:
    from uagents.chat import (
        chat_protocol_spec,
        ChatMessage,
        TextContent,
        EndSessionContent,
        ChatAcknowledgement
    )
    CHAT_PROTOCOL_AVAILABLE = True
except ImportError:
    print("[Warning] Chat protocol not available - ASI:One integration disabled")
    CHAT_PROTOCOL_AVAILABLE = False

# ============================================================================
# SCHEMAS
# ============================================================================

class ExtractedClaim(BaseModel):
    """A structured claim extracted from raw evidence"""
    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    claim_text: str
    canonical_text: str
    source_chunk_id: str
    source_agent: str
    entities: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    numbers: List[str] = Field(default_factory=list)
    direction: Literal["YES", "NO", "NEUTRAL"] = "NEUTRAL"
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    market_impact_score: float = Field(0.0, ge=0.0, le=1.0)
    estimated_probability_shift: float = Field(0.0, ge=-1.0, le=1.0)
    reason: Optional[str] = None
    extraction_method: Literal["claude", "heuristic"] = "heuristic"
    timestamp: datetime = Field(default_factory=datetime.now)


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
        "supports", "opposes", "mentions", "reported_by",
        "conflicts_with", "affects", "priced_in_by"
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


class ConsensusItem(BaseModel):
    """A consensus cluster of similar claims"""
    consensus_id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_claim: str
    direction: Literal["YES", "NO", "NEUTRAL"]
    source_count: int = 0
    source_agents: List[str] = Field(default_factory=list)
    source_diversity_score: float = 0.0
    agreement_level: Literal["high", "medium", "low"] = "medium"
    consensus_entropy: float = 0.0
    confidence: float = 0.5
    estimated_probability_shift: float = 0.0
    information_value: float = 0.0
    supporting_claim_ids: List[str] = Field(default_factory=list)
    opposing_claim_ids: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    numbers: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsensusLedger(BaseModel):
    """Collection of consensus items"""
    ledger_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    consensus_items: List[ConsensusItem] = Field(default_factory=list)

    def get_by_direction(self, direction: Literal["YES", "NO", "NEUTRAL"]) -> List[ConsensusItem]:
        return [item for item in self.consensus_items if item.direction == direction]

    def get_top_by_value(self, n: int = 5, direction: Optional[str] = None) -> List[ConsensusItem]:
        items = self.consensus_items
        if direction:
            items = self.get_by_direction(direction)
        return sorted(items, key=lambda x: x.information_value, reverse=True)[:n]


class CompressionMetrics(BaseModel):
    """Metrics about the compression process"""
    raw_token_count: int
    compressed_token_count: int
    compression_ratio: float
    token_budget: int
    total_claims_extracted: int = 0
    total_consensus_items: int = 0
    yes_consensus_count: int = 0
    no_consensus_count: int = 0
    neutral_consensus_count: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    claude_calls: int = 0
    claude_failures: int = 0
    heuristic_fallbacks: int = 0


class AdvancedCompressionResult(BaseModel):
    """Complete result of the advanced compression pipeline"""
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    market_id: str
    evidence_graph: EvidenceGraph
    consensus_ledger: ConsensusLedger
    top_supporting_evidence: List[ConsensusItem] = Field(default_factory=list)
    top_opposing_evidence: List[ConsensusItem] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    compressed_context: str
    metrics: CompressionMetrics
    mode: str = "graph-consensus"
    timestamp: datetime = Field(default_factory=datetime.now)


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
    aggressiveness: Optional[float] = 0.5  # 0-1, higher = more aggressive compression


class EnhancedCompressionResponse(BaseModel):
    """Enhanced compression response"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    compression_result: Optional[AdvancedCompressionResult] = None


# ============================================================================
# TOKEN COUNTING
# ============================================================================

def count_tokens(text: str) -> int:
    """Simple token counter (approximation)"""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except:
        # Fallback: ~1.3 tokens per word
        words = len(text.split())
        return int(words * 1.3)


# ============================================================================
# CLAIM EXTRACTION
# ============================================================================

SIGNAL_WORDS = {
    "confirmed", "official", "announced", "reported", "wins", "loses",
    "leads", "trails", "injury", "questionable", "out", "poll",
    "nomination", "award", "box office", "revenue", "inflation", "rate",
    "earnings", "price", "odds", "probability", "deadline", "ruling",
    "lawsuit", "trend", "viral", "market", "volume", "liquidity",
    "expected", "predicted", "forecast", "likely", "unlikely",
    "approval", "rejection", "passed", "failed", "winning", "losing"
}

YES_SIGNALS = {
    "wins", "winning", "leads", "leading", "frontrunner", "favorite",
    "approved", "passed", "nominated", "awarded", "confirmed", "yes",
    "positive", "growth", "increase", "gains", "surging", "momentum"
}

NO_SIGNALS = {
    "loses", "losing", "trails", "trailing", "underdog", "unlikely",
    "rejected", "failed", "denied", "no", "negative", "decline",
    "decrease", "losses", "falling", "slump", "controversy"
}

FILLER_WORDS = {
    "meanwhile", "however", "additionally", "furthermore", "moreover",
    "in other news", "unrelated", "separately", "aside from",
    "general", "various", "several", "some", "many", "few"
}


class HeuristicClaimExtractor:
    """Fallback claim extractor using heuristics"""

    def __init__(self):
        self.signal_words = SIGNAL_WORDS
        self.yes_signals = YES_SIGNALS
        self.no_signals = NO_SIGNALS
        self.filler_words = FILLER_WORDS

    def extract_claims(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        claims = []
        sentences = self._split_sentences(chunk.text)

        for sentence in sentences:
            if not self._is_relevant(sentence, market_question):
                continue

            entities = self._extract_entities(sentence)
            dates = self._extract_dates(sentence)
            numbers = self._extract_numbers(sentence)
            direction = self._classify_direction(sentence)
            confidence = self._calculate_confidence(sentence, entities, dates, numbers)
            market_impact = self._calculate_market_impact(sentence, direction)

            claim = ExtractedClaim(
                claim_text=sentence,
                canonical_text=sentence.lower().strip(),
                source_chunk_id=chunk.chunk_id,
                source_agent=chunk.source_agent,
                entities=entities,
                dates=dates,
                numbers=numbers,
                direction=direction,
                confidence=confidence,
                market_impact_score=market_impact,
                estimated_probability_shift=self._estimate_prob_shift(market_impact, direction),
                reason=f"Heuristic extraction from {chunk.source_agent}",
                extraction_method="heuristic"
            )
            claims.append(claim)

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _is_relevant(self, sentence: str, market_question: str) -> bool:
        sentence_lower = sentence.lower()
        has_signal = any(word in sentence_lower for word in self.signal_words)
        has_data = bool(re.search(r'\d+', sentence))
        has_entities = bool(re.search(r'\b[A-Z][a-z]+\b', sentence))
        has_filler = any(word in sentence_lower for word in self.filler_words)
        return (has_signal or has_data or has_entities) and not has_filler

    def _extract_entities(self, sentence: str) -> List[str]:
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
        return list(set(entities))

    def _extract_dates(self, sentence: str) -> List[str]:
        dates = []
        months = re.findall(
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
            sentence
        )
        dates.extend(months)
        years = re.findall(r'\b(20\d{2})\b', sentence)
        dates.extend(years)
        return list(set(dates))

    def _extract_numbers(self, sentence: str) -> List[str]:
        return re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', sentence)

    def _classify_direction(self, sentence: str) -> str:
        sentence_lower = sentence.lower()
        yes_count = sum(1 for word in self.yes_signals if word in sentence_lower)
        no_count = sum(1 for word in self.no_signals if word in sentence_lower)

        if yes_count > no_count and yes_count >= 1:
            return "YES"
        elif no_count > yes_count and no_count >= 1:
            return "NO"
        else:
            return "NEUTRAL"

    def _calculate_confidence(
        self,
        sentence: str,
        entities: List[str],
        dates: List[str],
        numbers: List[str]
    ) -> float:
        score = 0.3
        if entities:
            score += 0.15
        if dates:
            score += 0.15
        if numbers:
            score += 0.15

        sentence_lower = sentence.lower()
        signal_count = sum(1 for word in self.signal_words if word in sentence_lower)
        score += min(signal_count * 0.05, 0.25)
        return min(score, 0.95)

    def _calculate_market_impact(self, sentence: str, direction: str) -> float:
        if direction == "NEUTRAL":
            return 0.3

        sentence_lower = sentence.lower()
        impact = 0.5

        if "confirmed" in sentence_lower or "official" in sentence_lower:
            impact += 0.2

        if re.search(r'\d+', sentence):
            impact += 0.1

        return min(impact, 0.95)

    def _estimate_prob_shift(self, market_impact: float, direction: str) -> float:
        """
        Estimate probability shift - HEURISTIC VERSION.

        This is a simplified approximation. For production, consider:
        - Using Claude to estimate actual probability impact
        - Bayesian updating based on historical data
        - Calibration against market resolutions
        """
        if direction == "NEUTRAL":
            return 0.0

        # Heuristic: shift proportional to market impact
        # Max shift is ±15%
        shift = market_impact * 0.15

        if direction == "NO":
            shift = -shift

        return shift


class ClaudeClaimExtractor:
    """Claude-based claim extractor with fallback"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.heuristic_fallback = HeuristicClaimExtractor()

        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                self.client = None

    def extract_claims(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> Tuple[List[ExtractedClaim], str]:
        if not self.client:
            claims = self.heuristic_fallback.extract_claims(chunk, market_question, resolution_criteria)
            return claims, "heuristic_fallback"

        try:
            claims = self._extract_with_claude(chunk, market_question, resolution_criteria)
            return claims, "claude"
        except Exception as e:
            claims = self.heuristic_fallback.extract_claims(chunk, market_question, resolution_criteria)
            return claims, "heuristic_fallback"

    def _extract_with_claude(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        prompt = f"""You are extracting structured prediction-market evidence.

Market question:
{market_question}

Resolution criteria:
{resolution_criteria}

Evidence chunk:
{chunk.text}

Extract concise structured claims that could affect whether the market resolves YES or NO.

Return valid JSON only:

{{
  "claims": [
    {{
      "claim_text": "...",
      "canonical_text": "...",
      "entities": ["..."],
      "dates": ["..."],
      "numbers": ["..."],
      "direction": "YES | NO | NEUTRAL",
      "confidence": 0.0,
      "market_impact_score": 0.0,
      "estimated_probability_shift": 0.0,
      "reason": "..."
    }}
  ]
}}

Rules:
- direction means whether the claim supports YES, supports NO, or is unclear
- market_impact_score should reflect decision relevance (0.0 to 1.0)
- estimated_probability_shift should usually be between -0.15 and 0.15
- Return JSON only, no other text
"""

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from Claude response")

        claims = []
        for claim_data in data.get("claims", []):
            claim = ExtractedClaim(
                claim_text=claim_data.get("claim_text", ""),
                canonical_text=claim_data.get("canonical_text", claim_data.get("claim_text", "")),
                source_chunk_id=chunk.chunk_id,
                source_agent=chunk.source_agent,
                entities=claim_data.get("entities", []),
                dates=claim_data.get("dates", []),
                numbers=claim_data.get("numbers", []),
                direction=claim_data.get("direction", "NEUTRAL"),
                confidence=claim_data.get("confidence", 0.5),
                market_impact_score=claim_data.get("market_impact_score", 0.0),
                estimated_probability_shift=claim_data.get("estimated_probability_shift", 0.0),
                reason=claim_data.get("reason", ""),
                extraction_method="claude"
            )
            claims.append(claim)

        return claims


# ============================================================================
# EVIDENCE GRAPH BUILDER
# ============================================================================

class EvidenceGraphBuilder:
    """Builds an evidence graph from extracted claims"""

    def build_graph(
        self,
        market_id: str,
        market_question: str,
        claims: List[ExtractedClaim]
    ) -> EvidenceGraph:
        graph = EvidenceGraph(market_id=market_id)

        # Add market node
        market_node = GraphNode(
            node_id=f"market_{market_id}",
            node_type="market",
            label=market_question,
            properties={"question": market_question}
        )
        graph.nodes.append(market_node)

        entity_nodes = {}
        source_nodes = {}

        # Add claim nodes
        for claim in claims:
            claim_node = GraphNode(
                node_id=claim.claim_id,
                node_type="claim",
                label=claim.claim_text[:100],
                properties={
                    "text": claim.claim_text,
                    "canonical": claim.canonical_text,
                    "direction": claim.direction,
                    "confidence": claim.confidence,
                    "market_impact": claim.market_impact_score,
                    "prob_shift": claim.estimated_probability_shift
                }
            )
            graph.nodes.append(claim_node)

            # Add edge from claim to market
            if claim.direction == "YES":
                graph.edges.append(GraphEdge(
                    edge_type="supports",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score
                ))
            elif claim.direction == "NO":
                graph.edges.append(GraphEdge(
                    edge_type="opposes",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score
                ))

            # Add source node
            source_id = f"source_{claim.source_agent}"
            if source_id not in source_nodes:
                source_node = GraphNode(
                    node_id=source_id,
                    node_type="source",
                    label=claim.source_agent,
                    properties={"agent": claim.source_agent}
                )
                graph.nodes.append(source_node)
                source_nodes[source_id] = source_node

            graph.edges.append(GraphEdge(
                edge_type="reported_by",
                source_node_id=claim.claim_id,
                target_node_id=source_id,
                weight=claim.confidence
            ))

            # Add entity nodes
            for entity in claim.entities:
                entity_id = f"entity_{entity.replace(' ', '_').lower()}"
                if entity_id not in entity_nodes:
                    entity_node = GraphNode(
                        node_id=entity_id,
                        node_type="entity",
                        label=entity,
                        properties={"name": entity}
                    )
                    graph.nodes.append(entity_node)
                    entity_nodes[entity_id] = entity_node

                graph.edges.append(GraphEdge(
                    edge_type="mentions",
                    source_node_id=claim.claim_id,
                    target_node_id=entity_id,
                    weight=1.0
                ))

        # Add conflict edges
        self._add_conflict_edges(graph, claims)

        return graph

    def _add_conflict_edges(self, graph: EvidenceGraph, claims: List[ExtractedClaim]):
        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]

        for yes_claim in yes_claims:
            for no_claim in no_claims:
                yes_words = set(yes_claim.canonical_text.lower().split())
                no_words = set(no_claim.canonical_text.lower().split())
                overlap = yes_words & no_words

                if len(overlap) >= 3:
                    graph.edges.append(GraphEdge(
                        edge_type="conflicts_with",
                        source_node_id=yes_claim.claim_id,
                        target_node_id=no_claim.claim_id,
                        weight=len(overlap) / max(len(yes_words), len(no_words))
                    ))


# ============================================================================
# CONSENSUS CLUSTERING
# ============================================================================

class ConsensusClusterer:
    """Clusters similar claims into consensus items"""

    def __init__(self, similarity_threshold: float = 0.4):
        self.similarity_threshold = similarity_threshold

    def cluster_claims(self, claims: List[ExtractedClaim]) -> List[ConsensusItem]:
        if not claims:
            return []

        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]
        neutral_claims = [c for c in claims if c.direction == "NEUTRAL"]

        consensus_items = []
        consensus_items.extend(self._cluster_by_direction(yes_claims, "YES"))
        consensus_items.extend(self._cluster_by_direction(no_claims, "NO"))
        consensus_items.extend(self._cluster_by_direction(neutral_claims, "NEUTRAL"))

        return consensus_items

    def _cluster_by_direction(
        self,
        claims: List[ExtractedClaim],
        direction: str
    ) -> List[ConsensusItem]:
        if not claims:
            return []

        clusters = []
        used_claim_ids = set()

        for i, claim in enumerate(claims):
            if claim.claim_id in used_claim_ids:
                continue

            cluster_claims = [claim]
            used_claim_ids.add(claim.claim_id)

            for j, other_claim in enumerate(claims):
                if i == j or other_claim.claim_id in used_claim_ids:
                    continue

                similarity = self._calculate_similarity(claim, other_claim)
                if similarity >= self.similarity_threshold:
                    cluster_claims.append(other_claim)
                    used_claim_ids.add(other_claim.claim_id)

            consensus = self._create_consensus_item(cluster_claims, direction)
            clusters.append(consensus)

        return clusters

    def _calculate_similarity(self, claim1: ExtractedClaim, claim2: ExtractedClaim) -> float:
        tokens1 = set(claim1.canonical_text.lower().split())
        tokens2 = set(claim2.canonical_text.lower().split())

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _create_consensus_item(
        self,
        claims: List[ExtractedClaim],
        direction: str
    ) -> ConsensusItem:
        canonical_claim = max(claims, key=lambda c: c.market_impact_score)

        source_agents = list(set(c.source_agent for c in claims))
        source_diversity = len(source_agents) / max(len(claims), 1)

        confidences = [c.confidence for c in claims]
        avg_confidence = sum(confidences) / len(confidences)
        variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
        entropy = math.sqrt(variance)

        if entropy < 0.1:
            agreement = "high"
        elif entropy < 0.3:
            agreement = "medium"
        else:
            agreement = "low"

        prob_shifts = [c.estimated_probability_shift for c in claims]
        avg_prob_shift = sum(prob_shifts) / len(prob_shifts)

        all_entities = list(set(e for c in claims for e in c.entities))
        all_dates = list(set(d for c in claims for d in c.dates))
        all_numbers = list(set(n for c in claims for n in c.numbers))

        return ConsensusItem(
            canonical_claim=canonical_claim.claim_text,
            direction=direction,
            source_count=len(claims),
            source_agents=source_agents,
            source_diversity_score=source_diversity,
            agreement_level=agreement,
            consensus_entropy=entropy,
            confidence=avg_confidence,
            estimated_probability_shift=avg_prob_shift,
            information_value=0.0,
            supporting_claim_ids=[c.claim_id for c in claims],
            entities=all_entities,
            dates=all_dates,
            numbers=all_numbers,
            metadata={"cluster_size": len(claims)}
        )


# ============================================================================
# INFORMATION VALUE SCORING
# ============================================================================

class InformationValueScorer:
    """Scores consensus items by approximate information value"""

    def score_items(
        self,
        items: List[ConsensusItem],
        current_yes_price: Optional[float] = None
    ) -> List[ConsensusItem]:
        for item in items:
            item.information_value = self.calculate_information_value(
                item,
                items,
                current_yes_price
            )
        return items

    def calculate_information_value(
        self,
        item: ConsensusItem,
        all_items: List[ConsensusItem],
        current_yes_price: Optional[float] = None
    ) -> float:
        prob_shift_score = self._probability_shift_score(item)
        consensus_score = self._source_consensus_score(item)
        diversity_score = item.source_diversity_score
        recency_score = self._recency_score(item)
        contradiction_score = self._contradiction_importance(item)
        reliability_score = self._source_reliability(item)
        redundancy_score = self._redundancy_score(item, all_items)
        priced_in_score = self._priced_in_score(item, current_yes_price)

        value = (
            0.30 * prob_shift_score +
            0.20 * consensus_score +
            0.15 * diversity_score +
            0.15 * recency_score +
            0.10 * contradiction_score +
            0.10 * reliability_score -
            0.20 * redundancy_score -
            0.15 * priced_in_score
        )

        return max(0.0, min(1.0, value))

    def _probability_shift_score(self, item: ConsensusItem) -> float:
        abs_shift = abs(item.estimated_probability_shift)
        return min(abs_shift / 0.15, 1.0)

    def _source_consensus_score(self, item: ConsensusItem) -> float:
        return 1.0 - item.consensus_entropy

    def _recency_score(self, item: ConsensusItem) -> float:
        return 0.7  # Default moderate recency

    def _contradiction_importance(self, item: ConsensusItem) -> float:
        if item.opposing_claim_ids:
            return 0.8
        return 0.3

    def _source_reliability(self, item: ConsensusItem) -> float:
        if item.source_count >= 5:
            return 0.9
        elif item.source_count >= 3:
            return 0.7
        elif item.source_count >= 2:
            return 0.5
        else:
            return 0.3

    def _redundancy_score(self, item: ConsensusItem, all_items: List[ConsensusItem]) -> float:
        item_words = set(item.canonical_claim.lower().split())
        redundancy = 0.0

        for other in all_items:
            if other.consensus_id == item.consensus_id:
                continue

            other_words = set(other.canonical_claim.lower().split())
            overlap = item_words & other_words

            if overlap:
                redundancy += len(overlap) / max(len(item_words), len(other_words))

        if len(all_items) > 1:
            redundancy /= (len(all_items) - 1)

        return min(redundancy, 1.0)

    def _priced_in_score(self, item: ConsensusItem, current_yes_price: Optional[float]) -> float:
        if current_yes_price is None:
            return 0.5

        if item.direction == "YES" and current_yes_price > 0.6:
            return 0.7
        elif item.direction == "NO" and current_yes_price < 0.4:
            return 0.7
        else:
            return 0.3


# ============================================================================
# ADVANCED COMPRESSOR
# ============================================================================

class AdvancedCompressor:
    """Main compression pipeline orchestrator"""

    def __init__(self, use_claude: bool = True):
        self.use_claude = use_claude

        if use_claude:
            self.claim_extractor = ClaudeClaimExtractor()
        else:
            self.claim_extractor = HeuristicClaimExtractor()

        self.graph_builder = EvidenceGraphBuilder()
        self.consensus_clusterer = ConsensusClusterer(similarity_threshold=0.4)
        self.value_scorer = InformationValueScorer()

        self.stats = {
            "claude_calls": 0,
            "claude_failures": 0,
            "heuristic_fallbacks": 0,
        }

    def compress(self, request: EnhancedCompressionRequest) -> AdvancedCompressionResult:
        print(f"[AdvancedCompressor] Starting compression for market {request.market_id}")

        # Step 1: Extract claims
        all_claims = self._extract_all_claims(
            chunks=request.evidence_chunks,
            market_question=request.market_question,
            resolution_criteria=request.resolution_criteria
        )
        print(f"[AdvancedCompressor] Extracted {len(all_claims)} claims")

        # Step 2: Build evidence graph
        evidence_graph = self.graph_builder.build_graph(
            market_id=request.market_id,
            market_question=request.market_question,
            claims=all_claims
        )
        print(f"[AdvancedCompressor] Graph: {len(evidence_graph.nodes)} nodes, {len(evidence_graph.edges)} edges")

        # Step 3: Cluster into consensus items
        consensus_items = self.consensus_clusterer.cluster_claims(all_claims)
        print(f"[AdvancedCompressor] Created {len(consensus_items)} consensus items")

        # Step 4: Score by information value
        consensus_items = self.value_scorer.score_items(
            consensus_items,
            current_yes_price=request.current_yes_price
        )

        # Step 5: Apply aggressiveness filter
        aggressiveness = request.aggressiveness or 0.5
        threshold = aggressiveness * 0.6  # 0 = keep all, 1 = only keep top items
        consensus_items = [item for item in consensus_items if item.information_value >= threshold]
        print(f"[AdvancedCompressor] After aggressiveness filter ({aggressiveness:.2f}): {len(consensus_items)} items")

        consensus_ledger = ConsensusLedger(
            market_id=request.market_id,
            consensus_items=consensus_items
        )

        # Step 6: Identify contradictions and missing info
        contradictions = self._identify_contradictions(evidence_graph, consensus_items)
        missing_info = self._identify_missing_info(all_claims)

        # Step 7: Generate compressed context
        compressed_context = self._generate_compressed_context(
            request=request,
            consensus_ledger=consensus_ledger,
            evidence_graph=evidence_graph,
            contradictions=contradictions,
            missing_info=missing_info
        )

        # Calculate metrics
        raw_text = " ".join([chunk.text for chunk in request.evidence_chunks])
        raw_tokens = count_tokens(raw_text)
        compressed_tokens = count_tokens(compressed_context)
        compression_ratio = raw_tokens / compressed_tokens if compressed_tokens > 0 else 0.0

        metrics = CompressionMetrics(
            raw_token_count=raw_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=round(compression_ratio, 2),
            token_budget=request.token_budget or 3000,
            total_claims_extracted=len(all_claims),
            total_consensus_items=len(consensus_items),
            yes_consensus_count=len(consensus_ledger.get_by_direction("YES")),
            no_consensus_count=len(consensus_ledger.get_by_direction("NO")),
            neutral_consensus_count=len(consensus_ledger.get_by_direction("NEUTRAL")),
            graph_node_count=len(evidence_graph.nodes),
            graph_edge_count=len(evidence_graph.edges),
            claude_calls=self.stats["claude_calls"],
            claude_failures=self.stats["claude_failures"],
            heuristic_fallbacks=self.stats["heuristic_fallbacks"],
        )

        print(f"[AdvancedCompressor] Compression complete: {compression_ratio:.2f}x")

        result = AdvancedCompressionResult(
            request_id=request.request_id,
            market_id=request.market_id,
            evidence_graph=evidence_graph,
            consensus_ledger=consensus_ledger,
            top_supporting_evidence=consensus_ledger.get_top_by_value(5, "YES"),
            top_opposing_evidence=consensus_ledger.get_top_by_value(5, "NO"),
            contradictions=contradictions,
            missing_info=missing_info,
            compressed_context=compressed_context,
            metrics=metrics,
            mode=request.mode or "graph-consensus"
        )

        return result

    def _extract_all_claims(
        self,
        chunks: List[EnhancedEvidenceChunk],
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        all_claims = []

        for chunk in chunks:
            if isinstance(self.claim_extractor, ClaudeClaimExtractor):
                claims, method = self.claim_extractor.extract_claims(
                    chunk,
                    market_question,
                    resolution_criteria
                )

                if method == "claude":
                    self.stats["claude_calls"] += 1
                elif method == "heuristic_fallback":
                    self.stats["heuristic_fallbacks"] += 1
            else:
                claims = self.claim_extractor.extract_claims(
                    chunk,
                    market_question,
                    resolution_criteria
                )
                self.stats["heuristic_fallbacks"] += 1

            all_claims.extend(claims)

        return all_claims

    def _identify_contradictions(
        self,
        graph: EvidenceGraph,
        consensus_items: List[ConsensusItem]
    ) -> List[Dict[str, Any]]:
        contradictions = []
        conflict_edges = [e for e in graph.edges if e.edge_type == "conflicts_with"]

        claim_to_consensus = {}
        for item in consensus_items:
            for claim_id in item.supporting_claim_ids:
                claim_to_consensus[claim_id] = item

        seen_pairs = set()
        for edge in conflict_edges:
            consensus1 = claim_to_consensus.get(edge.source_node_id)
            consensus2 = claim_to_consensus.get(edge.target_node_id)

            if consensus1 and consensus2:
                pair_key = tuple(sorted([consensus1.consensus_id, consensus2.consensus_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                contradictions.append({
                    "claim1": consensus1.canonical_claim[:100],
                    "claim2": consensus2.canonical_claim[:100],
                    "direction1": consensus1.direction,
                    "direction2": consensus2.direction,
                    "weight": edge.weight
                })

        return contradictions[:5]

    def _identify_missing_info(self, claims: List[ExtractedClaim]) -> List[str]:
        missing_info = []

        has_numbers = any(claim.numbers for claim in claims)
        has_dates = any(claim.dates for claim in claims)
        has_official = any("official" in claim.claim_text.lower() for claim in claims)

        if not has_numbers:
            missing_info.append("Quantitative data or metrics")
        if not has_dates:
            missing_info.append("Recent time-specific information")
        if not has_official:
            missing_info.append("Official announcements or confirmations")

        missing_info.extend([
            "Real-time market data",
            "Updated news from the last 24 hours"
        ])

        return missing_info[:5]

    def _generate_compressed_context(
        self,
        request: EnhancedCompressionRequest,
        consensus_ledger: ConsensusLedger,
        evidence_graph: EvidenceGraph,
        contradictions: List[Dict[str, Any]],
        missing_info: List[str]
    ) -> str:
        lines = []

        lines.append("=" * 60)
        lines.append("COMPRESSED EVIDENCE CONTEXT")
        lines.append("=" * 60)
        lines.append("")

        lines.append("MARKET:")
        lines.append(f"{request.market_question}")
        lines.append("")

        if request.current_yes_price is not None:
            lines.append("MARKET PRICE:")
            lines.append(f"YES = {request.current_yes_price:.2f}, NO = {request.current_no_price:.2f}")
            lines.append("")

        lines.append("RESOLUTION CRITERIA:")
        lines.append(f"{request.resolution_criteria}")
        lines.append("")

        top_yes = consensus_ledger.get_top_by_value(5, "YES")
        if top_yes:
            lines.append("TOP YES EVIDENCE:")
            for i, item in enumerate(top_yes, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f}")
            lines.append("")

        top_no = consensus_ledger.get_top_by_value(5, "NO")
        if top_no:
            lines.append("TOP NO EVIDENCE:")
            for i, item in enumerate(top_no, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f}")
            lines.append("")

        if contradictions:
            lines.append("CONTRADICTIONS:")
            for i, contra in enumerate(contradictions, 1):
                lines.append(f"{i}. {contra['claim1']} [{contra['direction1']}]")
                lines.append(f"   vs. {contra['claim2']} [{contra['direction2']}]")
            lines.append("")

        if missing_info:
            lines.append("MISSING INFORMATION:")
            for info in missing_info:
                lines.append(f"- {info}")
            lines.append("")

        lines.append("GRAPH SUMMARY:")
        lines.append(f"- {len(evidence_graph.nodes)} nodes")
        lines.append(f"- {len(evidence_graph.edges)} edges")
        lines.append(f"- {len(consensus_ledger.consensus_items)} consensus clusters")
        lines.append("")

        return "\n".join(lines)


# ============================================================================
# UAGENT SETUP
# ============================================================================

AGENT_NAME = "compression_agent_standalone"
AGENT_SEED = "compression_agent_standalone_seed_change_in_production"
AGENT_PORT = 8002
AGENT_MAILBOX = True

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,
)

# Protocol for agent-to-agent communication
compression_protocol = Protocol("StandaloneContextCompression")

# Protocol for ASI:One/DeltaV interaction (if available)
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol("Chat", spec=chat_protocol_spec)

compressor = AdvancedCompressor(use_claude=True)


# ============================================================================
# ASI:ONE CHAT PROTOCOL HANDLER (for DeltaV/Agentverse users)
# ============================================================================

if CHAT_PROTOCOL_AVAILABLE:
    @chat_protocol.on_message(model=ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """
        Handle chat messages from ASI:One/DeltaV users.

        Expected input format (as text):
        {
            "market_question": "...",
            "resolution_criteria": "...",
            "evidence_chunks": [{...}],
            "current_yes_price": 0.5,
            "aggressiveness": 0.5
        }

        Or natural language query that we'll try to parse.
        """
        ctx.logger.info(f"[{AGENT_NAME}] Received chat message from {sender}")

        try:
            # Send acknowledgement
            await ctx.send(sender, ChatAcknowledgement())

            # Extract text from message content
            user_text = ""
            for content in msg.content:
                if isinstance(content, TextContent):
                    user_text += content.text

            ctx.logger.info(f"[{AGENT_NAME}] User query: {user_text[:200]}...")

            # Try to parse as JSON first
            try:
                request_data = json.loads(user_text)

                # Build compression request from JSON
                evidence_chunks = [
                    EnhancedEvidenceChunk(**chunk)
                    for chunk in request_data.get("evidence_chunks", [])
                ]

                request = EnhancedCompressionRequest(
                    market_id=request_data.get("market_id", "chat-market"),
                    market_question=request_data.get("market_question", ""),
                    resolution_criteria=request_data.get("resolution_criteria", ""),
                    current_yes_price=request_data.get("current_yes_price"),
                    current_no_price=request_data.get("current_no_price"),
                    evidence_chunks=evidence_chunks,
                    aggressiveness=request_data.get("aggressiveness", 0.5)
                )

            except json.JSONDecodeError:
                # Natural language query - provide help message
                help_message = """
**Compression Agent**

I compress evidence for prediction markets using graph-consensus algorithms.

**How to use:**

Send me a JSON request with:
```json
{
  "market_question": "Your market question",
  "resolution_criteria": "How the market resolves",
  "evidence_chunks": [
    {
      "market_id": "market-123",
      "source_agent": "web",
      "source_type": "news",
      "text": "Evidence text here..."
    }
  ],
  "current_yes_price": 0.5,
  "aggressiveness": 0.5
}
```

**Aggressiveness**: 0.0 = keep all evidence, 1.0 = only top items

**Returns**: Compressed context with top YES/NO evidence, contradictions, and information-value scores.
"""
                response_msg = ChatMessage(
                    content=[TextContent(text=help_message)]
                )
                await ctx.send(sender, response_msg)
                await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))
                return

            # Process compression
            result = compressor.compress(request)

            # Format response for user
            response_text = f"""
**Compression Complete**

**Metrics:**
- Raw tokens: {result.metrics.raw_token_count:,}
- Compressed tokens: {result.metrics.compressed_token_count:,}
- Compression ratio: {result.metrics.compression_ratio:.2f}x
- Claims extracted: {result.metrics.total_claims_extracted}
- Consensus items: {result.metrics.total_consensus_items}

**Compressed Context:**
```
{result.compressed_context}
```

**Top YES Evidence:** {result.metrics.yes_consensus_count} items
**Top NO Evidence:** {result.metrics.no_consensus_count} items
**Contradictions Found:** {len(result.contradictions)}
"""

            # Send response
            response_msg = ChatMessage(
                content=[TextContent(text=response_text)]
            )
            await ctx.send(sender, response_msg)

            ctx.logger.info(f"[{AGENT_NAME}] Chat response sent successfully")

        except Exception as e:
            ctx.logger.error(f"[{AGENT_NAME}] Chat handling failed: {e}")
            ctx.logger.error(traceback.format_exc())

            error_msg = ChatMessage(
                content=[TextContent(text=f"Error processing request: {str(e)}")]
            )
            await ctx.send(sender, error_msg)

        finally:
            # Always end the session
            await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))


# ============================================================================
# CUSTOM PROTOCOL HANDLER (for agent-to-agent communication)
# ============================================================================

@compression_protocol.on_message(model=EnhancedCompressionRequest)
async def handle_compression_request(ctx: Context, sender: str, msg: EnhancedCompressionRequest):
    """Handle advanced compression requests"""
    ctx.logger.info(f"[{AGENT_NAME}] Received compression request from {sender}")
    ctx.logger.info(f"Market ID: {msg.market_id}")
    ctx.logger.info(f"Evidence chunks: {len(msg.evidence_chunks)}")
    ctx.logger.info(f"Aggressiveness: {msg.aggressiveness or 0.5}")

    try:
        result = compressor.compress(msg)

        response = EnhancedCompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="success",
            compression_result=result
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Compression complete")
        ctx.logger.info(f"  Ratio: {result.metrics.compression_ratio:.2f}x")
        ctx.logger.info(f"  Claims: {result.metrics.total_claims_extracted}")
        ctx.logger.info(f"  Consensus items: {result.metrics.total_consensus_items}")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Compression failed: {e}")
        ctx.logger.error(traceback.format_exc())

        response = EnhancedCompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="error",
            error=str(e)
        )

        await ctx.send(sender, response)


# Include custom protocol for agent-to-agent communication
agent.include(compression_protocol, publish_manifest=False)

# Include ASI:One chat protocol if available
if CHAT_PROTOCOL_AVAILABLE:
    agent.include(chat_protocol, publish_manifest=True)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Standalone Compression Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Mode: Graph-Consensus Compression")
    ctx.logger.info(f"Ready to compress evidence contexts")

    # Protocol status
    ctx.logger.info("Custom protocol: ENABLED (agent-to-agent communication)")
    if CHAT_PROTOCOL_AVAILABLE:
        ctx.logger.info("ASI:One chat protocol: ENABLED (DeltaV compatible)")
    else:
        ctx.logger.info("ASI:One chat protocol: DISABLED (install uagents.chat)")

    if compressor.use_claude and compressor.claim_extractor.client:
        ctx.logger.info("Claude extraction: ENABLED")
    else:
        ctx.logger.info("Claude extraction: DISABLED (using heuristic fallback)")


if __name__ == "__main__":
    agent.run()
