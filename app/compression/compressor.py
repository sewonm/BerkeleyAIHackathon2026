"""Main compression pipeline"""

import hashlib
import json
import os
from typing import List, Optional

from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.schemas.compression import CompressionResult
from app.compression.scorer import ChunkScorer
from app.compression.protected_terms import extract_protected_terms
from app.compression.metrics import calculate_compression_ratio
from app.utils.token_counter import count_tokens
from app.utils.dedupe import deduplicate_chunks


class Compressor:
    """
    Compresses evidence chunks to fit within a token budget.

    Process:
    1. Check Redis cache — return instantly on hit
    2. Extract protected terms from market
    3. Score each chunk for relevance
    4. Deduplicate near-identical chunks
    5. Sort chunks by score
    6. Keep chunks until token budget is reached
    7. Write result to Redis cache + market key
    """

    def __init__(self):
        self.name = "Compressor"

    # ── Redis helpers ─────────────────────────────────────────────────────────

    def _redis(self):
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            r = redis.from_url(url, decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    def _cache_key(self, market_id: str, question: str) -> str:
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:12]
        return f"compression:cache:{market_id}:{question_hash}"

    def _read_cache(self, market_id: str, question: str) -> Optional[CompressionResult]:
        try:
            r = self._redis()
            if r is None:
                return None
            raw = r.get(self._cache_key(market_id, question))
            if raw:
                print(f"[Compressor] Redis cache HIT for {market_id}")
                data = json.loads(raw)
                data["cache_hit"] = True
                return CompressionResult(**data)
        except Exception:
            pass
        return None

    def _write_cache(self, market_id: str, question: str, result: CompressionResult):
        try:
            r = self._redis()
            if r is None:
                return
            payload = json.dumps(result.model_dump())
            r.setex(self._cache_key(market_id, question), 3600, payload)
            r.set(f"market:{market_id}:compressed", payload)
            print(f"[Compressor] Redis cache WRITE for {market_id}")
        except Exception as e:
            print(f"[Compressor] Redis write skipped: {e}")

    # ── Main compress ─────────────────────────────────────────────────────────

    def compress(
        self,
        market: Market,
        evidence_chunks: List[EvidenceChunk],
        token_budget: int = 3000
    ) -> CompressionResult:
        """
        Compress evidence chunks to fit within token budget.

        Args:
            market: The market being analyzed
            evidence_chunks: List of evidence chunks to compress
            token_budget: Maximum tokens for compressed output

        Returns:
            CompressionResult with compression metrics and compressed text
        """
        if not evidence_chunks:
            return CompressionResult(
                raw_token_count=0,
                compressed_token_count=0,
                compression_ratio=0.0,
                compressed_context="",
                kept_chunks=[],
                dropped_chunks=[],
                protected_terms=[]
            )

        # Step 0: Redis cache check
        cached = self._read_cache(market.market_id, market.question)
        if cached is not None:
            return cached

        # Step 1: Extract protected terms
        protected_terms = extract_protected_terms(market)
        print(f"[Compressor] Extracted {len(protected_terms)} protected terms")

        # Step 2: Score each chunk
        scorer = ChunkScorer(protected_terms)
        scored_chunks = []

        for chunk in evidence_chunks:
            score = scorer.score(chunk.text, market.question)
            scored_chunks.append({
                "text": chunk.text,
                "score": score,
                "source_type": chunk.source_type,
                "source_url": chunk.source_url or "unknown"
            })

        print(f"[Compressor] Scored {len(scored_chunks)} chunks")

        # Step 3: Deduplicate chunks
        deduped_chunks = deduplicate_chunks(scored_chunks, similarity_threshold=0.85)
        print(f"[Compressor] After deduplication: {len(deduped_chunks)} chunks")

        # Step 4: Sort by score (descending)
        sorted_chunks = sorted(deduped_chunks, key=lambda x: x['score'], reverse=True)

        # Step 5: Select chunks until budget is reached
        kept_chunks = []
        dropped_chunks = []
        current_tokens = 0

        # Add market context header (always included)
        context_header = f"Market: {market.title}\nQuestion: {market.question}\n\nEvidence:\n\n"
        header_tokens = count_tokens(context_header)
        current_tokens += header_tokens

        for chunk in sorted_chunks:
            chunk_tokens = count_tokens(chunk['text'])

            # Check if adding this chunk would exceed budget
            if current_tokens + chunk_tokens + 10 <= token_budget:  # +10 for separator
                kept_chunks.append(chunk)
                current_tokens += chunk_tokens + 10
            else:
                dropped_chunks.append(chunk)

        print(f"[Compressor] Kept {len(kept_chunks)} chunks, dropped {len(dropped_chunks)} chunks")

        # Step 6: Build compressed context
        compressed_parts = [context_header]
        for i, chunk in enumerate(kept_chunks, 1):
            compressed_parts.append(f"{i}. {chunk['text']}\n")

        compressed_context = '\n'.join(compressed_parts)

        # Step 7: Calculate metrics
        # Calculate raw token count from all chunks
        raw_text = '\n'.join([chunk['text'] for chunk in scored_chunks])
        raw_token_count = count_tokens(raw_text)
        compressed_token_count = count_tokens(compressed_context)
        compression_ratio = calculate_compression_ratio(raw_token_count, compressed_token_count)

        result = CompressionResult(
            raw_token_count=raw_token_count,
            compressed_token_count=compressed_token_count,
            compression_ratio=round(compression_ratio, 2),
            compressed_context=compressed_context,
            kept_chunks=kept_chunks,
            dropped_chunks=dropped_chunks,
            protected_terms=protected_terms
        )
        self._write_cache(market.market_id, market.question, result)
        return result
