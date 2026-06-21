"""
Evidence graph builder with Redis vector search for claim similarity.

Constructs a graph representation of evidence with nodes and edges.
ConsensusClusterer uses Redis HNSW vector index (sentence-transformers/all-MiniLM-L6-v2)
for semantic similarity, falling back to Jaccard if Redis or the model is unavailable.
"""

import math
import os
from typing import List, Optional, Tuple

from app.compression.schemas_advanced import (
    ConsensusItem,
    EvidenceGraph,
    ExtractedClaim,
    GraphEdge,
    GraphNode,
)


# ============================================================================
# Evidence Graph Builder
# ============================================================================

class EvidenceGraphBuilder:
    """Builds an evidence graph from extracted claims"""

    def build_graph(
        self,
        market_id: str,
        market_question: str,
        claims: List[ExtractedClaim],
    ) -> EvidenceGraph:
        graph = EvidenceGraph(market_id=market_id)

        market_node = GraphNode(
            node_id=f"market_{market_id}",
            node_type="market",
            label=market_question,
            properties={"question": market_question},
        )
        graph.add_node(market_node)

        entity_nodes: dict = {}
        source_nodes: dict = {}

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
                    "prob_shift": claim.estimated_probability_shift,
                },
            )
            graph.add_node(claim_node)

            if claim.direction == "YES":
                graph.add_edge(GraphEdge(
                    edge_type="supports",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score,
                ))
            elif claim.direction == "NO":
                graph.add_edge(GraphEdge(
                    edge_type="opposes",
                    source_node_id=claim.claim_id,
                    target_node_id=market_node.node_id,
                    weight=claim.market_impact_score,
                ))

            source_id = f"source_{claim.source_agent}"
            if source_id not in source_nodes:
                source_node = GraphNode(
                    node_id=source_id,
                    node_type="source",
                    label=claim.source_agent,
                    properties={"agent": claim.source_agent},
                )
                graph.add_node(source_node)
                source_nodes[source_id] = source_node

            graph.add_edge(GraphEdge(
                edge_type="reported_by",
                source_node_id=claim.claim_id,
                target_node_id=source_id,
                weight=claim.confidence,
            ))

            for entity in claim.entities:
                entity_id = f"entity_{entity.replace(' ', '_').lower()}"
                if entity_id not in entity_nodes:
                    entity_node = GraphNode(
                        node_id=entity_id,
                        node_type="entity",
                        label=entity,
                        properties={"name": entity},
                    )
                    graph.add_node(entity_node)
                    entity_nodes[entity_id] = entity_node

                graph.add_edge(GraphEdge(
                    edge_type="mentions",
                    source_node_id=claim.claim_id,
                    target_node_id=entity_id,
                    weight=1.0,
                ))

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
                    graph.add_edge(GraphEdge(
                        edge_type="conflicts_with",
                        source_node_id=yes_claim.claim_id,
                        target_node_id=no_claim.claim_id,
                        weight=len(overlap) / max(len(yes_words), len(no_words)),
                    ))


# ============================================================================
# Redis Vector Index
# ============================================================================

class RedisVectorIndex:
    """
    Manages a Redis HNSW vector index for semantic claim similarity.

    Embeds claims with sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast).
    Stores embeddings in Redis hashes under prefix 'claim:' so they don't
    collide with the market:* keys used by redis_service.py.
    Falls back gracefully to None if Redis or the model is unavailable.

    Cosine distance returned by Redis ∈ [0, 2]:
        0 = identical, 2 = opposite
    We convert: similarity = max(0, 1 - dist / 2) → ∈ [0, 1]
    """

    _INDEX_NAME = "signalforge_claims_vec"
    _KEY_PREFIX = "claim:"
    _DIM = 384  # all-MiniLM-L6-v2 output dimension

    def __init__(self, redis_url: Optional[str] = None):
        self._client = None
        self._model = None
        self._index_ready = False
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._init()

    def _init(self):
        # Try Redis connection
        try:
            from redis import Redis
            client = Redis.from_url(self._redis_url, decode_responses=False)
            client.ping()
            self._client = client
        except Exception as exc:
            print(f"[RedisVectorIndex] Redis unavailable ({exc}) — Jaccard fallback active")
            return

        # Try loading embedding model
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as exc:
            print(f"[RedisVectorIndex] sentence-transformers unavailable ({exc}) — Jaccard fallback active")
            return

        self._ensure_index()

    def _ensure_index(self):
        from redis.commands.search.field import TextField, VectorField
        from redis.commands.search.index_definition import IndexDefinition, IndexType

        try:
            self._client.ft(self._INDEX_NAME).info()
            self._index_ready = True
            print("[RedisVectorIndex] Using existing HNSW claim index")
            return
        except Exception:
            pass

        try:
            schema = (
                VectorField(
                    "vector",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self._DIM,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
                TextField("claim_id"),
            )
            definition = IndexDefinition(
                prefix=[self._KEY_PREFIX],
                index_type=IndexType.HASH,
            )
            self._client.ft(self._INDEX_NAME).create_index(
                fields=schema, definition=definition
            )
            self._index_ready = True
            print("[RedisVectorIndex] Created HNSW claim index")
        except Exception as exc:
            print(f"[RedisVectorIndex] Index creation failed ({exc}) — Jaccard fallback active")

    @property
    def available(self) -> bool:
        return self._client is not None and self._model is not None and self._index_ready

    def _embed(self, text: str) -> bytes:
        import numpy as np
        vec = self._model.encode(text)
        return np.array(vec, dtype="float32").tobytes()

    def upsert(self, claim: ExtractedClaim):
        """Store a claim's semantic embedding in Redis."""
        key = f"{self._KEY_PREFIX}{claim.claim_id}"
        self._client.hset(key, mapping={
            "vector": self._embed(claim.canonical_text),
            "claim_id": claim.claim_id,
        })

    def find_similar(
        self,
        query_claim: ExtractedClaim,
        candidate_ids: set,
        threshold: float,
    ) -> List[Tuple[str, float]]:
        """
        Return (claim_id, similarity) pairs from candidate_ids whose
        semantic similarity to query_claim meets the threshold.

        Uses Redis KNN — O(log n) via HNSW — instead of O(n) pairwise.
        """
        if not candidate_ids:
            return []

        from redis.commands.search.query import Query

        knn = min(len(candidate_ids) + 1, 50)
        query_vec = self._embed(query_claim.canonical_text)

        q = (
            Query(f"(*)=>[KNN {knn} @vector $vec AS dist]")
            .sort_by("dist")
            .return_fields("dist", "claim_id")
            .dialect(2)
        )

        try:
            res = self._client.ft(self._INDEX_NAME).search(
                q, query_params={"vec": query_vec}
            )
        except Exception as exc:
            print(f"[RedisVectorIndex] KNN query failed ({exc})")
            return []

        results = []
        for doc in res.docs:
            cid = getattr(doc, "claim_id", None)
            if cid and cid in candidate_ids:
                cosine_dist = float(getattr(doc, "dist", 2.0))
                similarity = max(0.0, 1.0 - cosine_dist / 2.0)
                if similarity >= threshold:
                    results.append((cid, similarity))

        return results

    def cleanup(self, claim_ids: List[str]):
        """Delete claim embeddings from Redis after clustering completes."""
        keys = [f"{self._KEY_PREFIX}{cid}" for cid in claim_ids]
        if keys:
            self._client.delete(*keys)


# ============================================================================
# Consensus Clustering
# ============================================================================

class ConsensusClusterer:
    """
    Clusters similar claims into consensus items.

    Primary path: Redis HNSW vector search via sentence-transformers embeddings
    (semantic similarity, captures paraphrases and synonym-heavy claims).

    Fallback path: Jaccard similarity on tokenized canonical text
    (used when Redis or sentence-transformers is unavailable).
    """

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        redis_url: Optional[str] = None,
    ):
        self.similarity_threshold = similarity_threshold
        self._vec_index = RedisVectorIndex(redis_url=redis_url)

        backend = "Redis vector search (HNSW)" if self._vec_index.available else "Jaccard (fallback)"
        print(f"[ConsensusClusterer] Similarity backend: {backend}")

    def cluster_claims(self, claims: List[ExtractedClaim]) -> List[ConsensusItem]:
        if not claims:
            return []

        # Pre-load all claim embeddings into Redis in one pass
        if self._vec_index.available:
            for claim in claims:
                self._vec_index.upsert(claim)

        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]
        neutral_claims = [c for c in claims if c.direction == "NEUTRAL"]

        consensus_items: List[ConsensusItem] = []
        consensus_items.extend(self._cluster_by_direction(yes_claims, "YES"))
        consensus_items.extend(self._cluster_by_direction(no_claims, "NO"))
        consensus_items.extend(self._cluster_by_direction(neutral_claims, "NEUTRAL"))

        # Clean up Redis embeddings so they don't accumulate across runs
        if self._vec_index.available:
            self._vec_index.cleanup([c.claim_id for c in claims])

        return consensus_items

    def _cluster_by_direction(
        self,
        claims: List[ExtractedClaim],
        direction: str,
    ) -> List[ConsensusItem]:
        if not claims:
            return []

        claim_map = {c.claim_id: c for c in claims}
        used_ids: set = set()
        clusters: List[ConsensusItem] = []

        for claim in claims:
            if claim.claim_id in used_ids:
                continue

            used_ids.add(claim.claim_id)
            cluster = [claim]

            remaining = set(claim_map) - used_ids

            if self._vec_index.available and remaining:
                similar = self._vec_index.find_similar(
                    query_claim=claim,
                    candidate_ids=remaining,
                    threshold=self.similarity_threshold,
                )
                for other_id, _ in similar:
                    if other_id not in used_ids:
                        cluster.append(claim_map[other_id])
                        used_ids.add(other_id)
            else:
                for other in claims:
                    if other.claim_id in used_ids:
                        continue
                    if self._jaccard_similarity(claim, other) >= self.similarity_threshold:
                        cluster.append(other)
                        used_ids.add(other.claim_id)

            clusters.append(self._create_consensus_item(cluster, direction))

        return clusters

    # ------------------------------------------------------------------
    # Fallback similarity

    def _jaccard_similarity(self, claim1: ExtractedClaim, claim2: ExtractedClaim) -> float:
        tokens1 = set(claim1.canonical_text.lower().split())
        tokens2 = set(claim2.canonical_text.lower().split())
        union = tokens1 | tokens2
        if not union:
            return 0.0
        return len(tokens1 & tokens2) / len(union)

    # ------------------------------------------------------------------
    # Consensus item creation (unchanged from original)

    def _create_consensus_item(
        self,
        claims: List[ExtractedClaim],
        direction: str,
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

        avg_prob_shift = sum(c.estimated_probability_shift for c in claims) / len(claims)

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
            entities=list(set(e for c in claims for e in c.entities)),
            dates=list(set(d for c in claims for d in c.dates)),
            numbers=list(set(n for c in claims for n in c.numbers)),
            metadata={"cluster_size": len(claims)},
        )
