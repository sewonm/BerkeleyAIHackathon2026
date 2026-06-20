"""Main compression pipeline"""

from typing import List

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
    1. Extract protected terms from market
    2. Score each chunk for relevance
    3. Deduplicate near-identical chunks
    4. Sort chunks by score
    5. Keep chunks until token budget is reached
    6. Return compression result with metrics
    """

    def __init__(self):
        self.name = "Compressor"

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

        return CompressionResult(
            raw_token_count=raw_token_count,
            compressed_token_count=compressed_token_count,
            compression_ratio=round(compression_ratio, 2),
            compressed_context=compressed_context,
            kept_chunks=kept_chunks,
            dropped_chunks=dropped_chunks,
            protected_terms=protected_terms
        )
