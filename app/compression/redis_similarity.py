"""
Redis-based vector similarity search for compression.

Uses Redis with RedisVL for semantic similarity detection between:
- Evidence chunks (deduplicate similar sources)
- Claims (enhance clustering beyond token overlap)
- Sources (identify redundant sources)

This helps the compressor identify:
1. Duplicate/similar content from different sources
2. Semantic similarity for better claim clustering
3. Source diversity measurement
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    import redis
    from redis.commands.search.field import TextField, VectorField, NumericField, TagField
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[RedisVectorSearch] Warning: redis package not installed")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[RedisVectorSearch] Warning: numpy not installed, using fallback")

from app.compression.schemas_advanced import (
    ExtractedClaim,
    EnhancedEvidenceChunk,
    ConsensusItem
)


# ============================================================================
# SIMPLE EMBEDDING GENERATOR (Fallback)
# ============================================================================

class SimpleEmbeddingGenerator:
    """
    Simple TF-IDF-like embedding generator for fallback.

    For production, use:
    - sentence-transformers (all-MiniLM-L6-v2)
    - OpenAI embeddings
    - Cohere embeddings
    """

    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.vocab = {}
        self.idf = {}

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding"""
        # Normalize text
        text_lower = text.lower().strip()
        words = text_lower.split()

        # Create a simple embedding using word hashing
        embedding = [0.0] * self.embedding_dim

        for i, word in enumerate(words):
            # Hash word to embedding dimensions
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)

            for j in range(self.embedding_dim):
                # Use hash to distribute word into embedding space
                if (hash_val >> j) & 1:
                    embedding[j] += 1.0 / (i + 1)  # Position weighting

        # Normalize
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


# ============================================================================
# SENTENCE TRANSFORMER EMBEDDING GENERATOR (Recommended)
# ============================================================================

class SentenceTransformerEmbedding:
    """
    Sentence transformer-based embedding generator.

    Uses all-MiniLM-L6-v2 (384 dimensions) for high-quality semantic embeddings.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embedding_dim = 384

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"[SentenceTransformer] Loaded {model_name} (dim={self.embedding_dim})")
        except ImportError:
            print("[SentenceTransformer] sentence-transformers not installed, using fallback")
            self.model = None

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence transformers"""
        if self.model is None:
            # Fallback to simple embedding
            simple_gen = SimpleEmbeddingGenerator(embedding_dim=384)
            return simple_gen.generate_embedding(text)

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# ============================================================================
# REDIS VECTOR SEARCH CLIENT
# ============================================================================

class RedisVectorSearch:
    """
    Redis-based vector similarity search for compression.

    Features:
    - Store and search evidence chunks by semantic similarity
    - Store and search claims by semantic similarity
    - Measure source diversity
    - Cache compression results
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        embedding_model: str = "sentence-transformer",
        use_cache: bool = True
    ):
        """
        Initialize Redis vector search.

        Args:
            redis_url: Redis connection URL (default: from REDIS_URL env var)
            embedding_model: "sentence-transformer" or "simple"
            use_cache: Whether to cache compression results
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.use_cache = use_cache
        self.enabled = False
        self.client = None

        # Initialize embedding generator
        if embedding_model == "sentence-transformer":
            self.embedder = SentenceTransformerEmbedding()
        else:
            self.embedder = SimpleEmbeddingGenerator(embedding_dim=256)

        self.embedding_dim = self.embedder.embedding_dim

        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                self.enabled = True
                print(f"[RedisVectorSearch] Connected to Redis at {self.redis_url}")

                # Create indexes
                self._create_indexes()
            except Exception as e:
                print(f"[RedisVectorSearch] Failed to connect to Redis: {e}")
                print("[RedisVectorSearch] Running without Redis (no vector search)")
                self.enabled = False
        else:
            print("[RedisVectorSearch] Redis not available, running without vector search")

    def _create_indexes(self):
        """Create Redis search indexes for vector search"""
        if not self.enabled:
            return

        try:
            # Index for evidence chunks
            self._create_chunk_index()

            # Index for claims
            self._create_claim_index()

            print("[RedisVectorSearch] Indexes created successfully")
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to create indexes: {e}")

    def _create_chunk_index(self):
        """Create index for evidence chunks"""
        index_name = "idx:chunks"

        try:
            # Try to get existing index
            self.client.ft(index_name).info()
            print(f"[RedisVectorSearch] Index {index_name} already exists")
            return
        except:
            # Index doesn't exist, create it
            pass

        schema = (
            TextField("$.chunk_id", as_name="chunk_id"),
            TextField("$.market_id", as_name="market_id"),
            TextField("$.source_agent", as_name="source_agent"),
            TextField("$.text", as_name="text"),
            VectorField(
                "$.embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="embedding"
            ),
        )

        definition = IndexDefinition(prefix=["chunk:"], index_type=IndexType.JSON)
        self.client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"[RedisVectorSearch] Created index {index_name}")

    def _create_claim_index(self):
        """Create index for claims"""
        index_name = "idx:claims"

        try:
            self.client.ft(index_name).info()
            print(f"[RedisVectorSearch] Index {index_name} already exists")
            return
        except:
            pass

        schema = (
            TextField("$.claim_id", as_name="claim_id"),
            TextField("$.market_id", as_name="market_id"),
            TextField("$.canonical_text", as_name="canonical_text"),
            TagField("$.direction", as_name="direction"),
            NumericField("$.confidence", as_name="confidence"),
            VectorField(
                "$.embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="embedding"
            ),
        )

        definition = IndexDefinition(prefix=["claim:"], index_type=IndexType.JSON)
        self.client.ft(index_name).create_index(fields=schema, definition=definition)
        print(f"[RedisVectorSearch] Created index {index_name}")

    # ========================================================================
    # EVIDENCE CHUNK OPERATIONS
    # ========================================================================

    def add_evidence_chunk(
        self,
        chunk: EnhancedEvidenceChunk,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """
        Add an evidence chunk to Redis.

        Args:
            chunk: Evidence chunk
            embedding: Pre-computed embedding (optional)

        Returns:
            True if added successfully
        """
        if not self.enabled:
            return False

        try:
            # Generate embedding if not provided
            if embedding is None:
                embedding = self.embedder.generate_embedding(chunk.text)

            # Store in Redis
            doc = {
                "chunk_id": chunk.chunk_id,
                "market_id": chunk.market_id,
                "source_agent": chunk.source_agent,
                "source_type": chunk.source_type,
                "text": chunk.text,
                "embedding": embedding,
                "timestamp": chunk.timestamp or datetime.now().isoformat(),
            }

            key = f"chunk:{chunk.chunk_id}"
            self.client.json().set(key, "$", doc)

            return True
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to add chunk: {e}")
            return False

    def find_similar_chunks(
        self,
        text: str,
        market_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.8
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find similar evidence chunks.

        Args:
            text: Query text
            market_id: Market ID to search within
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of (chunk_data, similarity_score) tuples
        """
        if not self.enabled:
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedder.generate_embedding(text)

            # Build Redis query
            query = (
                Query(f"@market_id:{{{market_id}}} => [KNN {top_k} @embedding $vec AS score]")
                .return_fields("chunk_id", "source_agent", "text", "score")
                .sort_by("score")
                .dialect(2)
            )

            # Convert embedding to bytes
            if NUMPY_AVAILABLE:
                vec_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
            else:
                # Manual conversion
                import struct
                vec_bytes = b''.join(struct.pack('f', x) for x in query_embedding)

            # Execute search
            results = self.client.ft("idx:chunks").search(
                query,
                query_params={"vec": vec_bytes}
            )

            # Filter by similarity threshold
            similar_chunks = []
            for doc in results.docs:
                # Redis returns distance, convert to similarity
                distance = float(doc.score)
                similarity = 1.0 - distance  # Cosine distance to similarity

                if similarity >= similarity_threshold:
                    chunk_data = {
                        "chunk_id": doc.chunk_id,
                        "source_agent": doc.source_agent,
                        "text": doc.text,
                    }
                    similar_chunks.append((chunk_data, similarity))

            return similar_chunks
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to find similar chunks: {e}")
            return []

    # ========================================================================
    # CLAIM OPERATIONS
    # ========================================================================

    def add_claim(
        self,
        claim: ExtractedClaim,
        market_id: str,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """
        Add a claim to Redis.

        Args:
            claim: Extracted claim
            market_id: Market ID
            embedding: Pre-computed embedding (optional)

        Returns:
            True if added successfully
        """
        if not self.enabled:
            return False

        try:
            if embedding is None:
                embedding = self.embedder.generate_embedding(claim.canonical_text)

            doc = {
                "claim_id": claim.claim_id,
                "market_id": market_id,
                "canonical_text": claim.canonical_text,
                "direction": claim.direction,
                "confidence": claim.confidence,
                "market_impact_score": claim.market_impact_score,
                "embedding": embedding,
            }

            key = f"claim:{claim.claim_id}"
            self.client.json().set(key, "$", doc)

            return True
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to add claim: {e}")
            return False

    def find_similar_claims(
        self,
        claim: ExtractedClaim,
        market_id: str,
        direction: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.6
    ) -> List[Tuple[str, float]]:
        """
        Find similar claims for clustering.

        Args:
            claim: Query claim
            market_id: Market ID to search within
            direction: Filter by direction (YES/NO/NEUTRAL)
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of (claim_id, similarity_score) tuples
        """
        if not self.enabled:
            return []

        try:
            query_embedding = self.embedder.generate_embedding(claim.canonical_text)

            # Build query with optional direction filter
            if direction:
                base_query = f"@market_id:{{{market_id}}} @direction:{{{direction}}}"
            else:
                base_query = f"@market_id:{{{market_id}}}"

            query = (
                Query(f"{base_query} => [KNN {top_k} @embedding $vec AS score]")
                .return_fields("claim_id", "canonical_text", "score")
                .sort_by("score")
                .dialect(2)
            )

            if NUMPY_AVAILABLE:
                vec_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
            else:
                import struct
                vec_bytes = b''.join(struct.pack('f', x) for x in query_embedding)

            results = self.client.ft("idx:claims").search(
                query,
                query_params={"vec": vec_bytes}
            )

            similar_claims = []
            for doc in results.docs:
                # Skip self
                if doc.claim_id == claim.claim_id:
                    continue

                distance = float(doc.score)
                similarity = 1.0 - distance

                if similarity >= similarity_threshold:
                    similar_claims.append((doc.claim_id, similarity))

            return similar_claims
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to find similar claims: {e}")
            return []

    # ========================================================================
    # SOURCE DIVERSITY ANALYSIS
    # ========================================================================

    def measure_source_diversity(
        self,
        chunks: List[EnhancedEvidenceChunk],
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Measure source diversity using vector similarity.

        Args:
            chunks: List of evidence chunks
            similarity_threshold: Threshold for considering sources duplicate

        Returns:
            Diversity metrics
        """
        if not self.enabled or len(chunks) == 0:
            return {
                "total_sources": len(chunks),
                "unique_sources": len(set(c.source_agent for c in chunks)),
                "duplicate_groups": [],
                "diversity_score": 1.0
            }

        try:
            # Add all chunks to Redis
            for chunk in chunks:
                self.add_evidence_chunk(chunk)

            # Find duplicate groups
            seen = set()
            duplicate_groups = []

            for chunk in chunks:
                if chunk.chunk_id in seen:
                    continue

                similar = self.find_similar_chunks(
                    chunk.text,
                    chunk.market_id,
                    top_k=len(chunks),
                    similarity_threshold=similarity_threshold
                )

                if len(similar) > 0:
                    group = [chunk.chunk_id]
                    for similar_chunk, sim_score in similar:
                        if similar_chunk["chunk_id"] not in seen:
                            group.append(similar_chunk["chunk_id"])
                            seen.add(similar_chunk["chunk_id"])

                    if len(group) > 1:
                        duplicate_groups.append(group)

                seen.add(chunk.chunk_id)

            # Calculate diversity score
            # 1.0 = all unique, 0.0 = all duplicates
            unique_count = len(chunks) - sum(len(g) - 1 for g in duplicate_groups)
            diversity_score = unique_count / len(chunks) if len(chunks) > 0 else 1.0

            return {
                "total_sources": len(chunks),
                "unique_sources": len(set(c.source_agent for c in chunks)),
                "effective_unique_sources": unique_count,
                "duplicate_groups": duplicate_groups,
                "diversity_score": diversity_score
            }
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to measure source diversity: {e}")
            return {
                "total_sources": len(chunks),
                "unique_sources": len(set(c.source_agent for c in chunks)),
                "duplicate_groups": [],
                "diversity_score": 1.0
            }

    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================

    def cache_compression_result(
        self,
        market_id: str,
        evidence_hash: str,
        result: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        Cache a compression result.

        Args:
            market_id: Market ID
            evidence_hash: Hash of the evidence (for cache key)
            result: Compression result
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        if not self.enabled or not self.use_cache:
            return False

        try:
            key = f"compression:cache:{market_id}:{evidence_hash}"
            self.client.setex(key, ttl, json.dumps(result))
            return True
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to cache result: {e}")
            return False

    def get_cached_compression(
        self,
        market_id: str,
        evidence_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached compression result.

        Args:
            market_id: Market ID
            evidence_hash: Hash of the evidence

        Returns:
            Cached result or None
        """
        if not self.enabled or not self.use_cache:
            return None

        try:
            key = f"compression:cache:{market_id}:{evidence_hash}"
            cached = self.client.get(key)

            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to get cached result: {e}")
            return None

    # ========================================================================
    # UTILITY
    # ========================================================================

    def clear_market_data(self, market_id: str) -> bool:
        """
        Clear all data for a market.

        Args:
            market_id: Market ID

        Returns:
            True if cleared successfully
        """
        if not self.enabled:
            return False

        try:
            # Delete chunks
            chunk_keys = self.client.keys(f"chunk:*")
            for key in chunk_keys:
                data = self.client.json().get(key)
                if data and data.get("market_id") == market_id:
                    self.client.delete(key)

            # Delete claims
            claim_keys = self.client.keys(f"claim:*")
            for key in claim_keys:
                data = self.client.json().get(key)
                if data and data.get("market_id") == market_id:
                    self.client.delete(key)

            # Delete cache
            cache_keys = self.client.keys(f"compression:cache:{market_id}:*")
            for key in cache_keys:
                self.client.delete(key)

            return True
        except Exception as e:
            print(f"[RedisVectorSearch] Failed to clear market data: {e}")
            return False
