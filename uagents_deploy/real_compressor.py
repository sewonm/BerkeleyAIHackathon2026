"""
Real Compression Engine - Actually compresses evidence into compact graph format

This module implements true information-theoretic compression that REDUCES token count
while preserving high-value market-relevant information.
"""

import re
import json
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class Sentence:
    """A single sentence from evidence"""
    text: str
    source_agent: str
    chunk_id: str
    tokens: int

    # Extracted features
    numbers: List[float] = None
    dates: List[str] = None
    entities: List[str] = None
    signal_words: List[str] = None

    # Computed scores
    info_value: float = 0.0
    direction: str = "NEUTRAL"  # YES, NO, NEUTRAL
    prob_shift: float = 0.0

    def __post_init__(self):
        if self.numbers is None:
            self.numbers = []
        if self.dates is None:
            self.dates = []
        if self.entities is None:
            self.entities = []
        if self.signal_words is None:
            self.signal_words = []


@dataclass
class CompactClaim:
    """Compact representation of a claim for output"""
    id: str
    text: str  # Shortened to max 80 chars
    dir: str  # Y, N, or NE (neutral)
    val: float  # Information value 0-1
    shift: float  # Probability shift
    src_count: int  # Number of sources merged

    def to_compact_list(self) -> List[Any]:
        """Ultra-compact array format [text, dir_code, val, shift]"""
        dir_code = 1 if self.dir == "Y" else (-1 if self.dir == "N" else 0)
        return [
            self.text[:50],  # Shortened text
            dir_code,
            round(self.val, 2),
            round(self.shift, 3)
        ]

    def token_count(self) -> int:
        """Estimate token count of JSON representation"""
        return len(json.dumps(self.to_compact_list())) // 4  # Rough estimate


@dataclass
class CompactEdge:
    """Compact edge representation"""
    from_id: str
    to_id: str
    rel: str  # sup (supports), con (conflicts), sim (similar)
    w: float  # Weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "rel": self.rel,
            "w": round(self.w, 2)
        }


class RealCompressor:
    """
    Real compression engine that actually reduces token count
    """

    # Signal words for direction classification
    YES_SIGNALS = {
        "won", "wins", "winning", "leads", "leading", "frontrunner", "favorite",
        "approved", "passed", "nominated", "awarded", "confirmed", "yes",
        "positive", "growth", "increase", "gains", "surging", "momentum",
        "strong", "excellent", "exceptional", "healthy", "solid"
    }

    NO_SIGNALS = {
        "lost", "loses", "losing", "trails", "trailing", "underdog", "unlikely",
        "rejected", "failed", "denied", "no", "negative", "decline",
        "decrease", "losses", "falling", "slump", "controversy",
        "injured", "questionable", "struggled", "weak", "barely"
    }

    FILLER_PHRASES = [
        "in a", "very", "quite", "really", "extremely", "the match was",
        "showing", "played", "was in", "has a", "have a", "there is",
        "it is", "they are", "this is", "that was", "which is"
    ]

    def __init__(self, similarity_threshold: float = 0.5):
        self.similarity_threshold = similarity_threshold

    def compress(
        self,
        evidence_chunks: List[Dict[str, Any]],
        market_question: str,
        token_budget: int = 200
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Compress evidence into compact graph format

        Returns:
            (compressed_output, metrics)
        """
        # Phase 1: Parse into sentences
        all_sentences = self._parse_all_sentences(evidence_chunks)
        raw_tokens = sum(s.tokens for s in all_sentences)

        # Phase 2: Remove exact duplicates
        unique_sentences = self._deduplicate_exact(all_sentences)

        # Phase 3: Cluster similar sentences
        clusters = self._cluster_similar(unique_sentences)

        # Phase 4: Create canonical claims from clusters
        canonical_claims = self._create_canonical_claims(clusters)

        # Phase 5: Score information value
        scored_claims = self._score_claims(canonical_claims, market_question)

        # Phase 6: Filter to token budget
        compressed_claims = self._filter_to_budget(scored_claims, token_budget)

        # Phase 7: Build compact edges
        edges = self._build_edges(compressed_claims)

        # Phase 8: Create final output
        output = self._create_compact_output(compressed_claims, edges)

        # Calculate metrics
        compressed_tokens = self._count_output_tokens(output)
        metrics = {
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(raw_tokens / compressed_tokens, 2) if compressed_tokens > 0 else 0,
            "claims_extracted": len(all_sentences),
            "claims_after_dedup": len(unique_sentences),
            "claims_after_clustering": len(canonical_claims),
            "final_claims": len(compressed_claims),
            "edges": len(edges),
            "token_budget": token_budget,
            "budget_used_pct": round(100 * compressed_tokens / token_budget, 1) if token_budget > 0 else 0
        }

        return output, metrics

    def _parse_all_sentences(self, evidence_chunks: List[Dict[str, Any]]) -> List[Sentence]:
        """Parse evidence into individual sentences"""
        sentences = []

        for chunk in evidence_chunks:
            text = chunk.get("text", "")
            source_agent = chunk.get("source_agent", "unknown")
            chunk_id = chunk.get("chunk_id", str(uuid4()))

            # Split into sentences
            raw_sentences = re.split(r'[.!?]+', text)

            for sent in raw_sentences:
                sent = sent.strip()
                if len(sent) < 15:  # Skip very short sentences
                    continue

                # Extract features
                numbers = self._extract_numbers(sent)
                dates = self._extract_dates(sent)
                entities = self._extract_entities(sent)
                signal_words = self._extract_signal_words(sent)
                direction = self._classify_direction(sent)
                prob_shift = self._estimate_prob_shift(sent, direction)

                tokens = len(sent.split())

                sentence = Sentence(
                    text=sent,
                    source_agent=source_agent,
                    chunk_id=chunk_id,
                    tokens=tokens,
                    numbers=numbers,
                    dates=dates,
                    entities=entities,
                    signal_words=signal_words,
                    direction=direction,
                    prob_shift=prob_shift
                )

                sentences.append(sentence)

        return sentences

    def _deduplicate_exact(self, sentences: List[Sentence]) -> List[Sentence]:
        """Remove exact duplicates (case-insensitive)"""
        seen = set()
        unique = []

        for sent in sentences:
            normalized = sent.text.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(sent)

        return unique

    def _cluster_similar(self, sentences: List[Sentence]) -> List[List[Sentence]]:
        """Cluster similar sentences using token overlap"""
        clusters = []
        used = set()

        for i, sent1 in enumerate(sentences):
            if i in used:
                continue

            cluster = [sent1]
            used.add(i)

            tokens1 = set(sent1.text.lower().split())

            for j, sent2 in enumerate(sentences[i+1:], start=i+1):
                if j in used:
                    continue

                tokens2 = set(sent2.text.lower().split())
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)

                if overlap >= self.similarity_threshold:
                    cluster.append(sent2)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _create_canonical_claims(self, clusters: List[List[Sentence]]) -> List[Sentence]:
        """Create one canonical sentence per cluster"""
        canonical_claims = []

        for cluster in clusters:
            # Pick the most informative sentence as canonical
            best = max(cluster, key=lambda s: len(s.numbers) + len(s.dates) + len(s.signal_words))

            # Merge source information
            # Count how many sources contributed to this cluster
            sources = set(s.source_agent for s in cluster)

            # Store merge count in a hacky way (we'll use this later)
            best.text = best.text  # Keep text as-is
            # Add metadata about sources
            best.source_agent = f"{len(sources)}_sources" if len(sources) > 1 else best.source_agent

            canonical_claims.append(best)

        return canonical_claims

    def _score_claims(self, claims: List[Sentence], market_question: str) -> List[Sentence]:
        """Score each claim's information value"""
        for claim in claims:
            score = 0.0

            # Numbers are valuable
            score += 0.25 * min(len(claim.numbers), 3) / 3.0

            # Dates are valuable
            score += 0.20 * min(len(claim.dates), 2) / 2.0

            # Signal words are valuable
            score += 0.20 * min(len(claim.signal_words), 3) / 3.0

            # Entities are somewhat valuable
            score += 0.15 * min(len(claim.entities), 3) / 3.0

            # Strong direction is valuable
            if claim.direction != "NEUTRAL":
                score += 0.10

            # High probability shift is valuable
            score += 0.10 * min(abs(claim.prob_shift), 0.1) / 0.1

            claim.info_value = min(score, 1.0)

        return claims

    def _filter_to_budget(self, claims: List[Sentence], token_budget: int) -> List[CompactClaim]:
        """Filter claims to fit within token budget"""
        # Sort by information value
        sorted_claims = sorted(claims, key=lambda c: c.info_value, reverse=True)

        result = []
        tokens_used = 0

        for claim in sorted_claims:
            # Remove filler words to shorten text
            shortened_text = self._remove_fillers(claim.text)

            # Count sources
            src_count = int(claim.source_agent.split("_")[0]) if "_sources" in claim.source_agent else 1

            # Create compact claim
            compact = CompactClaim(
                id=f"c{len(result)+1}",
                text=shortened_text,
                dir=claim.direction[0],  # Y, N, or NE
                val=claim.info_value,
                shift=claim.prob_shift,
                src_count=src_count
            )

            claim_tokens = compact.token_count()

            if tokens_used + claim_tokens <= token_budget:
                result.append(compact)
                tokens_used += claim_tokens
            else:
                # Budget exhausted
                break

        return result

    def _build_edges(self, claims: List[CompactClaim]) -> List[CompactEdge]:
        """Build edges between related claims"""
        edges = []

        for i, claim1 in enumerate(claims):
            for j, claim2 in enumerate(claims[i+1:], start=i+1):
                # Check for relationships

                # Same direction = supports
                if claim1.dir == claim2.dir and claim1.dir != "N":
                    edges.append(CompactEdge(
                        from_id=claim1.id,
                        to_id=claim2.id,
                        rel="sup",  # supports
                        w=0.7
                    ))

                # Opposite directions = conflicts
                elif (claim1.dir == "Y" and claim2.dir == "N") or (claim1.dir == "N" and claim2.dir == "Y"):
                    edges.append(CompactEdge(
                        from_id=claim1.id,
                        to_id=claim2.id,
                        rel="con",  # conflicts
                        w=0.6
                    ))

        return edges

    def _create_compact_output(self, claims: List[CompactClaim], edges: List[CompactEdge]) -> Dict[str, Any]:
        """Create final ULTRA-compact JSON output using arrays"""

        # Group by direction
        yes_claims = [c for c in claims if c.dir == "Y"]
        no_claims = [c for c in claims if c.dir == "N"]

        # Sort by value
        yes_claims.sort(key=lambda c: c.val, reverse=True)
        no_claims.sort(key=lambda c: c.val, reverse=True)

        # Ultra-compact format:
        # claims: [[text, dir_code, val, shift], ...]
        # dir_code: 1=YES, -1=NO, 0=NEUTRAL
        # No edges to save space!
        return {
            "claims": [c.to_compact_list() for c in claims],
            "yes": [i for i, c in enumerate(claims) if c.dir == "Y"],
            "no": [i for i, c in enumerate(claims) if c.dir == "N"]
        }

    def _count_output_tokens(self, output: Dict[str, Any]) -> int:
        """Count tokens in output JSON"""
        json_str = json.dumps(output, separators=(',', ':'))  # Compact JSON
        return len(json_str) // 4  # Approximate token count

    # Helper methods for feature extraction

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numbers from text"""
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|percent)?\b', text)
        return [float(re.sub(r'[^\d.]', '', n)) for n in numbers if re.sub(r'[^\d.]', '', n)]

    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []
        # Simple date patterns
        months = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}', text, re.IGNORECASE)
        years = re.findall(r'\b20\d{2}\b', text)
        temporal = re.findall(r'\b(?:yesterday|today|tomorrow|week|month|year)\b', text, re.IGNORECASE)
        return months + years + temporal

    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities (capitalized words)"""
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        return list(set(entities))

    def _extract_signal_words(self, text: str) -> List[str]:
        """Extract signal words"""
        text_lower = text.lower()
        words = []
        for word in self.YES_SIGNALS | self.NO_SIGNALS:
            if word in text_lower:
                words.append(word)
        return words

    def _classify_direction(self, text: str) -> str:
        """Classify if text supports YES, NO, or NEUTRAL"""
        text_lower = text.lower()

        yes_count = sum(1 for word in self.YES_SIGNALS if word in text_lower)
        no_count = sum(1 for word in self.NO_SIGNALS if word in text_lower)

        if yes_count > no_count:
            return "YES"
        elif no_count > yes_count:
            return "NO"
        else:
            return "NEUTRAL"

    def _estimate_prob_shift(self, text: str, direction: str) -> float:
        """Estimate probability shift from this claim"""
        # Extract percentages or numbers
        numbers = self._extract_numbers(text)

        if numbers:
            # If we have numbers, use them to estimate impact
            max_num = max(numbers)
            if max_num > 10:
                shift = min(max_num / 100, 0.15)
            else:
                shift = min(max_num / 100, 0.05)
        else:
            # Default based on signal words
            shift = 0.03

        # Direction determines sign
        if direction == "NO":
            shift = -shift
        elif direction == "NEUTRAL":
            shift = 0.0

        return shift

    def _remove_fillers(self, text: str) -> str:
        """Remove filler phrases to shorten text"""
        result = text
        for filler in self.FILLER_PHRASES:
            result = re.sub(r'\b' + re.escape(filler) + r'\b', '', result, flags=re.IGNORECASE)

        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()

        return result
