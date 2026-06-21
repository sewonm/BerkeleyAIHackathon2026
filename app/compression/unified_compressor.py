"""
UnifiedCompressor — 4-layer compression pipeline backed by Redis.

Layer 1: Relevance scoring       (ChunkScorer — keyword + protected-term overlap)
Layer 2: Semantic deduplication  (Jaccard similarity — removes near-duplicate chunks)
Layer 3: Symbolic compression    (SymbolicLayer — variable substitution, Redis-persisted)
Layer 4: Token budget + cache    (trim to fit Claude, write result to Redis)

All Redis operations degrade gracefully if Redis is unavailable.
Returns CompressionResult — same interface as the base Compressor.
"""

import hashlib
import json
import os
import re
from collections import Counter
from typing import List, Optional, Tuple

from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.schemas.compression import CompressionResult
from app.compression.scorer import ChunkScorer
from app.compression.protected_terms import extract_protected_terms
from app.compression.metrics import calculate_compression_ratio
from app.utils.token_counter import count_tokens
from app.utils.dedupe import deduplicate_chunks


# ── SymbolicLayer ──────────────────────────────────────────────────────────────

class SymbolicLayer:
    """
    Rewrites repeated multi-word entities as short variables to cut token count.
    Variable mappings are persisted in Redis for cross-session consistency —
    so "Kendrick Lamar" is always KL across every analysis that mentions him.

    Example
    -------
    Input chunks mention "2026 FIFA World Cup" 12 times and "Kylian Mbappe" 8 times.

    Output:
        VARS: KM=Kylian Mbappe, WC26=2026 FIFA World Cup
        "KM injured ahead of WC26 knockout stage..."
        "France face WC26 quarterfinal without KM..."
    """

    MIN_FREQUENCY = 3       # entity must appear this many times to earn a variable
    MAX_PHRASE_WORDS = 4    # longest phrase to consider
    MIN_PHRASE_WORDS = 2    # single words are not abbreviated
    MAX_VARS = 12           # cap to keep the legend readable

    _STOP = frozenset({
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was',
        'were', 'has', 'have', 'its', 'their', 'will', 'not', 'but', 'also',
    })

    def __init__(self, market_id: str, protected_terms: List[str]):
        self.market_id = market_id
        self.protected_terms = protected_terms
        self._r = self._connect()
        self._assigned: dict = {}   # entity → variable (session + Redis)
        self._used_vars: set = set()
        self._counter = 0
        self._load_from_redis()

    # -- Redis helpers ---------------------------------------------------------

    def _connect(self):
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    def _redis_key(self) -> str:
        return f"compression:vars:{self.market_id}"

    def _load_from_redis(self):
        if self._r:
            try:
                stored = self._r.hgetall(self._redis_key())
                self._assigned.update(stored)
                self._used_vars.update(stored.values())
            except Exception:
                pass

    def _persist(self, entity: str, var: str):
        self._assigned[entity] = var
        self._used_vars.add(var)
        if self._r:
            try:
                self._r.hset(self._redis_key(), entity, var)
                self._r.expire(self._redis_key(), 86400)  # 24 h TTL
            except Exception:
                pass

    # -- Variable generation ---------------------------------------------------

    def _initials(self, phrase: str) -> str:
        words = phrase.split()
        # Strip years from words before taking initials
        year = re.search(r'\b(20\d{2})\b', phrase)
        year_suffix = year.group(1)[2:] if year else ""
        filtered = [w for w in words if not re.fullmatch(r'\d+', w) and w.lower() not in self._STOP and len(w) > 2]
        initials = ''.join(w[0].upper() for w in filtered)
        if year_suffix:
            initials = initials + year_suffix
        return initials or f"V{self._counter}"

    def _assign_var(self, phrase: str) -> str:
        if phrase in self._assigned:
            return self._assigned[phrase]
        base = self._initials(phrase)
        var = base
        suffix = 1
        while var in self._used_vars:
            var = f"{base}{suffix}"
            suffix += 1
        self._counter += 1
        self._persist(phrase, var)
        return var

    # -- Phrase extraction -----------------------------------------------------

    def _count_phrases(self, texts: List[str]) -> Counter:
        counts: Counter = Counter()
        for text in texts:
            # Consecutive capitalised words (proper nouns) — normalise to title case
            for n in range(self.MAX_PHRASE_WORDS, self.MIN_PHRASE_WORDS - 1, -1):
                pat = r'\b' + r'\s+'.join([r'[A-Z][a-zA-Z]+'] * n) + r'\b'
                for match in re.findall(pat, text):
                    counts[match.title()] += 1
            # Protected terms — store in title case to merge with proper-noun hits
            for term in self.protected_terms:
                if len(term.split()) >= self.MIN_PHRASE_WORDS:
                    n = len(re.findall(re.escape(term), text, re.IGNORECASE))
                    if n:
                        counts[term.title()] += n
        return counts

    # -- Public API ------------------------------------------------------------

    def compress(self, chunks: List[dict]) -> Tuple[List[dict], str]:
        """
        Substitute repeated entities with variables in chunk texts.

        Returns
        -------
        compressed_chunks : list of chunk dicts with rewritten text
        legend            : "VARS: KM=Kylian Mbappe, WC26=2026 FIFA World Cup"
        """
        if not chunks:
            return chunks, ""

        texts = [c.get("text", "") for c in chunks]
        phrase_counts = self._count_phrases(texts)

        candidates = [
            (phrase, cnt) for phrase, cnt in phrase_counts.items()
            if cnt >= self.MIN_FREQUENCY
        ]
        # Longest phrase first so replacements don't partially overlap
        candidates.sort(key=lambda x: len(x[0]), reverse=True)

        var_map: dict = {}
        for phrase, _ in candidates[:self.MAX_VARS]:
            var_map[phrase] = self._assign_var(phrase)

        if not var_map:
            return chunks, ""

        # Apply substitutions
        compressed: List[dict] = []
        for chunk in chunks:
            text = chunk.get("text", "")
            for phrase, var in sorted(var_map.items(), key=lambda x: len(x[0]), reverse=True):
                text = re.sub(re.escape(phrase), var, text, flags=re.IGNORECASE)
            compressed.append({**chunk, "text": text})

        legend = "VARS: " + ", ".join(
            f"{v}={k}" for k, v in sorted(var_map.items(), key=lambda x: x[1])
        )
        return compressed, legend


# ── UnifiedCompressor ──────────────────────────────────────────────────────────

class UnifiedCompressor:
    """
    Drop-in replacement for Compressor that runs all 4 layers.

    Redis is used for:
      • Variable mappings  compression:vars:{market_id}   (SymbolicLayer)
      • Result cache       compression:unified:{id}:{hash} (1 h TTL)
      • Market snapshot    market:{id}:compressed          (shared with orchestrator)
    """

    def __init__(self):
        self.name = "UnifiedCompressor"

    # -- Redis helpers ---------------------------------------------------------

    def _r(self):
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    def _cache_key(self, market_id: str, chunks: List[EvidenceChunk]) -> str:
        h = hashlib.md5("".join(c.text for c in chunks).encode()).hexdigest()[:12]
        return f"compression:unified:{market_id}:{h}"

    def _read_cache(self, market_id: str, chunks: List[EvidenceChunk]) -> Optional[CompressionResult]:
        try:
            r = self._r()
            if r is None:
                return None
            raw = r.get(self._cache_key(market_id, chunks))
            if raw:
                print(f"[UnifiedCompressor] Cache HIT — {market_id}")
                return CompressionResult(**json.loads(raw))
        except Exception:
            pass
        return None

    def _write_cache(self, market_id: str, chunks: List[EvidenceChunk], result: CompressionResult):
        try:
            r = self._r()
            if r is None:
                return
            payload = json.dumps(result.model_dump())
            r.setex(self._cache_key(market_id, chunks), 3600, payload)
            r.set(f"market:{market_id}:compressed", payload)
            print(f"[UnifiedCompressor] Cache WRITE — {market_id}")
        except Exception as e:
            print(f"[UnifiedCompressor] Redis write skipped: {e}")

    # -- Main pipeline ---------------------------------------------------------

    def compress(
        self,
        market: Market,
        evidence_chunks: List[EvidenceChunk],
        token_budget: int = 3000,
    ) -> CompressionResult:
        """Run the 4-layer pipeline and return a CompressionResult."""

        if not evidence_chunks:
            return CompressionResult(
                raw_token_count=0,
                compressed_token_count=0,
                compression_ratio=0.0,
                compressed_context="",
                kept_chunks=[],
                dropped_chunks=[],
                protected_terms=[],
            )

        # ── Layer 0: Redis cache check ────────────────────────────────────────
        cached = self._read_cache(market.market_id, evidence_chunks)
        if cached:
            return cached

        protected_terms = extract_protected_terms(market)

        # ── Layer 1: Relevance scoring ────────────────────────────────────────
        scorer = ChunkScorer(protected_terms)
        scored: List[dict] = []
        for chunk in evidence_chunks:
            scored.append({
                "text": chunk.text,
                "score": scorer.score(chunk.text, market.question),
                "source_type": chunk.source_type,
                "source_url": chunk.source_url or "unknown",
            })
        print(f"[UnifiedCompressor] Layer 1: scored {len(scored)} chunks")

        # ── Layer 2: Semantic deduplication ───────────────────────────────────
        deduped = deduplicate_chunks(scored, similarity_threshold=0.85)
        print(f"[UnifiedCompressor] Layer 2: {len(deduped)} unique chunks after dedup")

        # Sort by score, keep top 2× budget-worth as candidates for symbolic layer
        sorted_chunks = sorted(deduped, key=lambda x: x["score"], reverse=True)
        candidates: List[dict] = []
        running = 0
        for c in sorted_chunks:
            t = count_tokens(c["text"])
            if running + t > token_budget * 2:
                break
            candidates.append(c)
            running += t

        # ── Layer 3: Symbolic compression ─────────────────────────────────────
        symbolic = SymbolicLayer(market.market_id, protected_terms)
        compressed_candidates, legend = symbolic.compress(candidates)
        if legend:
            print(f"[UnifiedCompressor] Layer 3: {legend[:100]}")
        else:
            print("[UnifiedCompressor] Layer 3: no repeated entities — symbolic layer skipped")

        # ── Layer 4: Token budget enforcement ─────────────────────────────────
        header = f"Market: {market.title}\nQuestion: {market.question}\n\n"
        if legend:
            header += legend + "\n\n"
        header += "Evidence:\n\n"

        kept: List[dict] = []
        dropped: List[dict] = []
        current = count_tokens(header)

        for chunk in compressed_candidates:
            t = count_tokens(chunk["text"])
            if current + t + 10 <= token_budget:
                kept.append(chunk)
                current += t + 10
            else:
                dropped.append(chunk)

        # Chunks that never made it into the candidate pool
        dropped.extend(sorted_chunks[len(candidates):])

        context = header + "\n".join(f"{i}. {c['text']}" for i, c in enumerate(kept, 1))

        raw_text = "\n".join(c["text"] for c in scored)
        raw_tokens = count_tokens(raw_text)
        compressed_tokens = count_tokens(context)
        ratio = calculate_compression_ratio(raw_tokens, compressed_tokens)

        print(
            f"[UnifiedCompressor] Layer 4: {len(kept)} kept / {len(dropped)} dropped "
            f"| {ratio:.1f}x compression | {compressed_tokens} tokens"
        )

        result = CompressionResult(
            raw_token_count=raw_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=round(ratio, 2),
            compressed_context=context,
            kept_chunks=kept,
            dropped_chunks=dropped,
            protected_terms=protected_terms,
        )

        self._write_cache(market.market_id, evidence_chunks, result)
        return result
