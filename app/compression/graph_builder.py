"""
Evidence graph builder.

Constructs a graph representation of evidence with nodes and edges.
"""

from typing import List
import math

from app.compression.schemas_advanced import (
    ExtractedClaim,
    EvidenceGraph,
    GraphNode,
    GraphEdge,
    ConsensusItem,
)


class EvidenceGraphBuilder:
    """Builds an evidence graph from extracted claims"""

    def __init__(self):
        pass

    def build_graph(
        self,
        market_id: str,
        market_question: str,
        claims: List[ExtractedClaim]
    ) -> EvidenceGraph:
        """
        Build evidence graph from claims.

        Args:
            market_id: Market ID
            market_question: Market question
            claims: List of extracted claims

        Returns:
            Evidence graph
        """
        graph = EvidenceGraph(market_id=market_id)

        # Add market node
        market_node = GraphNode(
            node_id=f"market_{market_id}",
            node_type="market",
            label=market_question,
            properties={"question": market_question}
        )
        graph.add_node(market_node)

        # Track entities and sources
        entity_nodes = {}
        source_nodes = {}

        # Add claim nodes and related entities
        for claim in claims:
            # Add claim node
            claim_node = GraphNode(
                node_id=claim.claim_id,
                node_type="claim",
                label=claim.claim_text[:100],  # Truncate for label
                properties={
                    "text": claim.claim_text,
                    "canonical": claim.canonical_text,
                    "direction": claim.direction,
                    "confidence": claim.confidence,
                    "market_impact": claim.market_impact_score,
                    "prob_shift": claim.estimated_probability_shift
                }
            )
            graph.add_node(claim_node)

            # Add edge from claim to market (supports/opposes)
            if claim.direction == "YES":
                graph.add_edge(GraphEdge(
                    edge_type="supports",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score
                ))
            elif claim.direction == "NO":
                graph.add_edge(GraphEdge(
                    edge_type="opposes",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score
                ))

            # Add source node and edge
            source_id = f"source_{claim.source_agent}"
            if source_id not in source_nodes:
                source_node = GraphNode(
                    node_id=source_id,
                    node_type="source",
                    label=claim.source_agent,
                    properties={"agent": claim.source_agent}
                )
                graph.add_node(source_node)
                source_nodes[source_id] = source_node

            graph.add_edge(GraphEdge(
                edge_type="reported_by",
                source_node_id=claim.claim_id,
                target_node_id=source_id,
                weight=claim.confidence
            ))

            # Add entity nodes and edges
            for entity in claim.entities:
                entity_id = f"entity_{entity.replace(' ', '_').lower()}"
                if entity_id not in entity_nodes:
                    entity_node = GraphNode(
                        node_id=entity_id,
                        node_type="entity",
                        label=entity,
                        properties={"name": entity}
                    )
                    graph.add_node(entity_node)
                    entity_nodes[entity_id] = entity_node

                graph.add_edge(GraphEdge(
                    edge_type="mentions",
                    source_node_id=claim.claim_id,
                    target_node_id=entity_id,
                    weight=1.0
                ))

        # Add conflict edges between opposing claims
        self._add_conflict_edges(graph, claims)

        return graph

    def _add_conflict_edges(self, graph: EvidenceGraph, claims: List[ExtractedClaim]):
        """Add conflict edges between opposing claims"""
        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]

        # For simplicity, connect YES claims to NO claims if they're about similar topics
        for yes_claim in yes_claims:
            for no_claim in no_claims:
                # Simple heuristic: if they share entities or keywords, they might conflict
                yes_words = set(yes_claim.canonical_text.lower().split())
                no_words = set(no_claim.canonical_text.lower().split())

                overlap = yes_words & no_words
                if len(overlap) >= 3:  # At least 3 shared words
                    graph.add_edge(GraphEdge(
                        edge_type="conflicts_with",
                        source_node_id=yes_claim.claim_id,
                        target_node_id=no_claim.claim_id,
                        weight=len(overlap) / max(len(yes_words), len(no_words))
                    ))


# ============================================================================
# Consensus Clustering
# ============================================================================

class ConsensusClusterer:
    """
    Clusters similar claims into consensus items.

    Uses token-based similarity as fallback.
    Can be enhanced with embeddings or Redis vector search.
    """

    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold

    def cluster_claims(self, claims: List[ExtractedClaim]) -> List[ConsensusItem]:
        """
        Cluster claims into consensus items.

        Args:
            claims: List of extracted claims

        Returns:
            List of consensus items
        """
        if not claims:
            return []

        # Group claims by direction first
        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]
        neutral_claims = [c for c in claims if c.direction == "NEUTRAL"]

        consensus_items = []

        # Cluster each direction separately
        consensus_items.extend(self._cluster_by_direction(yes_claims, "YES"))
        consensus_items.extend(self._cluster_by_direction(no_claims, "NO"))
        consensus_items.extend(self._cluster_by_direction(neutral_claims, "NEUTRAL"))

        return consensus_items

    def _cluster_by_direction(
        self,
        claims: List[ExtractedClaim],
        direction: str
    ) -> List[ConsensusItem]:
        """Cluster claims of the same direction"""
        if not claims:
            return []

        clusters = []
        used_claim_ids = set()

        for i, claim in enumerate(claims):
            if claim.claim_id in used_claim_ids:
                continue

            # Start a new cluster
            cluster_claims = [claim]
            used_claim_ids.add(claim.claim_id)

            # Find similar claims
            for j, other_claim in enumerate(claims):
                if i == j or other_claim.claim_id in used_claim_ids:
                    continue

                similarity = self._calculate_similarity(claim, other_claim)
                if similarity >= self.similarity_threshold:
                    cluster_claims.append(other_claim)
                    used_claim_ids.add(other_claim.claim_id)

            # Create consensus item
            consensus = self._create_consensus_item(cluster_claims, direction)
            clusters.append(consensus)

        return clusters

    def _calculate_similarity(self, claim1: ExtractedClaim, claim2: ExtractedClaim) -> float:
        """
        Calculate similarity between two claims using Jaccard similarity.

        Args:
            claim1: First claim
            claim2: Second claim

        Returns:
            Similarity score (0-1)
        """
        # Tokenize
        tokens1 = set(claim1.canonical_text.lower().split())
        tokens2 = set(claim2.canonical_text.lower().split())

        # Jaccard similarity
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
        """Create a consensus item from a cluster of claims"""
        # Use the highest-impact claim as canonical
        canonical_claim = max(claims, key=lambda c: c.market_impact_score)

        # Aggregate source info
        source_agents = list(set(c.source_agent for c in claims))
        source_diversity = len(source_agents) / max(len(claims), 1)

        # Calculate consensus entropy
        # For simplicity, entropy based on confidence variance
        confidences = [c.confidence for c in claims]
        avg_confidence = sum(confidences) / len(confidences)
        variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
        entropy = math.sqrt(variance)  # Simplified entropy

        # Determine agreement level
        if entropy < 0.1:
            agreement = "high"
        elif entropy < 0.3:
            agreement = "medium"
        else:
            agreement = "low"

        # Aggregate probability shifts
        prob_shifts = [c.estimated_probability_shift for c in claims]
        avg_prob_shift = sum(prob_shifts) / len(prob_shifts)

        # Collect all entities, dates, numbers
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
            information_value=0.0,  # Will be calculated later
            supporting_claim_ids=[c.claim_id for c in claims],
            entities=all_entities,
            dates=all_dates,
            numbers=all_numbers,
            metadata={"cluster_size": len(claims)}
        )
