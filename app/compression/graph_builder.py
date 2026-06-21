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

    Priority: Redis HNSW vector search → sentence-transformers cosine → Jaccard
    """

    _INDEX = "sf_cluster_idx"
    _PREFIX = "sf_claim:"
    _DIM = 384
    _st_model = None  # loaded once, shared across instances

    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self._redis_client = None
        self._redis_ready = False

    def cluster_claims(self, claims: List[ExtractedClaim]) -> List[ConsensusItem]:
        if not claims:
            return []

        self._redis_ready = self._try_setup_redis(claims)

        try:
            yes_claims = [c for c in claims if c.direction == "YES"]
            no_claims = [c for c in claims if c.direction == "NO"]
            neutral_claims = [c for c in claims if c.direction == "NEUTRAL"]

            results = []
            results.extend(self._cluster_by_direction(yes_claims, "YES"))
            results.extend(self._cluster_by_direction(no_claims, "NO"))
            results.extend(self._cluster_by_direction(neutral_claims, "NEUTRAL"))
            return results
        finally:
            if self._redis_ready:
                self._cleanup_redis()

    # ------------------------------------------------------------------
    # Redis HNSW setup / teardown
    # ------------------------------------------------------------------

    def _try_setup_redis(self, claims: List[ExtractedClaim]) -> bool:
        """Build a temporary HNSW index in Redis with all claim embeddings."""
        try:
            import os
            import numpy as np
            from sentence_transformers import SentenceTransformer
            import redis as redis_lib
            from redis.commands.search.field import VectorField
            from redis.commands.search.indexDefinition import IndexDefinition, IndexType

            if ConsensusClusterer._st_model is None:
                ConsensusClusterer._st_model = SentenceTransformer("all-MiniLM-L6-v2")

            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis_client = redis_lib.from_url(url, decode_responses=False)
            self._redis_client.ping()

            # Drop stale index if present
            try:
                self._redis_client.ft(self._INDEX).dropindex(delete_documents=True)
            except Exception:
                pass

            self._redis_client.ft(self._INDEX).create_index(
                [VectorField("emb", "HNSW", {
                    "TYPE": "FLOAT32", "DIM": self._DIM, "DISTANCE_METRIC": "COSINE"
                })],
                definition=IndexDefinition(prefix=[self._PREFIX], index_type=IndexType.HASH)
            )

            # Batch-encode and upsert all claims
            texts = [c.canonical_text for c in claims]
            embeddings = ConsensusClusterer._st_model.encode(texts, batch_size=32)
            pipe = self._redis_client.pipeline(transaction=False)
            for claim, emb in zip(claims, embeddings):
                pipe.hset(f"{self._PREFIX}{claim.claim_id}", mapping={
                    "emb": emb.astype(np.float32).tobytes(),
                    "cid": claim.claim_id,
                })
            pipe.execute()
            return True
        except Exception:
            return False

    def _cleanup_redis(self):
        try:
            self._redis_client.ft(self._INDEX).dropindex(delete_documents=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def _cluster_by_direction(self, claims: List[ExtractedClaim], direction: str) -> List[ConsensusItem]:
        if not claims:
            return []

        clusters = []
        used_claim_ids = set()
        claim_by_id = {c.claim_id: c for c in claims}

        for claim in claims:
            if claim.claim_id in used_claim_ids:
                continue

            cluster_claims = [claim]
            used_claim_ids.add(claim.claim_id)

            candidates = {c.claim_id for c in claims if c.claim_id not in used_claim_ids}

            if self._redis_ready and candidates:
                for cid in self._redis_knn(claim, candidates):
                    cluster_claims.append(claim_by_id[cid])
                    used_claim_ids.add(cid)
            else:
                for other in claims:
                    if other.claim_id in used_claim_ids:
                        continue
                    if self._calculate_similarity(claim, other) >= self.similarity_threshold:
                        cluster_claims.append(other)
                        used_claim_ids.add(other.claim_id)

            clusters.append(self._create_consensus_item(cluster_claims, direction))

        return clusters

    def _redis_knn(self, query_claim: ExtractedClaim, candidate_ids: set) -> List[str]:
        """KNN query against Redis HNSW index. Returns claim_ids above threshold."""
        try:
            import numpy as np
            from redis.commands.search.query import Query

            vec = ConsensusClusterer._st_model.encode([query_claim.canonical_text])[0]
            k = min(len(candidate_ids) + 1, 50)

            q = (Query(f"(*)=>[KNN {k} @emb $vec AS dist]")
                 .sort_by("dist")
                 .return_fields("dist", "cid")
                 .dialect(2))

            results = self._redis_client.ft(self._INDEX).search(
                q, query_params={"vec": vec.astype(np.float32).tobytes()}
            )

            matches = []
            for doc in results.docs:
                cid = getattr(doc, "cid", None)
                if not cid or cid not in candidate_ids:
                    continue
                similarity = max(0.0, 1.0 - float(getattr(doc, "dist", 1.0)))
                if similarity >= self.similarity_threshold:
                    matches.append(cid)
            return matches
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Pairwise fallback (no Redis)
    # ------------------------------------------------------------------

    def _calculate_similarity(self, claim1: ExtractedClaim, claim2: ExtractedClaim) -> float:
        score = self._semantic_similarity(claim1.canonical_text, claim2.canonical_text)
        if score is not None:
            return score
        tokens1 = set(claim1.canonical_text.lower().split())
        tokens2 = set(claim2.canonical_text.lower().split())
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union) if union else 0.0

    def _semantic_similarity(self, text1: str, text2: str) -> float | None:
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
            if ConsensusClusterer._st_model is None:
                ConsensusClusterer._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            emb = ConsensusClusterer._st_model.encode([text1, text2])
            cosine = float(np.dot(emb[0], emb[1]) / (np.linalg.norm(emb[0]) * np.linalg.norm(emb[1])))
            return max(0.0, cosine)
        except Exception:
            return None

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
