"""
Ultra Compression - Text-based format that actually compresses

Output format is compact text with indices for YES/NO claims
"""

import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict


class UltraCompressor:
    """
    Ultra-compact compression that outputs text format:

    Output example:
    YES: France beat Brazil 2-1 (0.85)|Mbappe scored 2 (0.72)|Defense strong (0.65)
    NO: Pogba injured (0.68)
    """

    YES_SIGNALS = {
        "won", "wins", "winning", "leads", "leading", "favorite",
        "approved", "passed", "yes", "positive", "growth", "increase",
        "strong", "excellent", "exceptional", "healthy", "solid", "beat", "defeated"
    }

    NO_SIGNALS = {
        "lost", "loses", "losing", "trails", "unlikely",
        "rejected", "failed", "no", "negative", "decline",
        "injured", "struggled", "weak", "barely"
    }

    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold

    def compress(
        self,
        evidence_chunks: List[Dict[str, Any]],
        market_question: str,
        token_budget: int = 200
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compress evidence into ultra-compact text format

        Returns:
            (compressed_text, metrics)
        """
        # Step 1: Parse and extract all sentences
        sentences = self._parse_sentences(evidence_chunks)
        raw_tokens = sum(len(s.split()) for s in sentences)

        # Step 2: Remove exact duplicates
        unique_sentences = list(set(s.lower().strip() for s in sentences))

        # Step 3: Cluster similar sentences
        clusters = self._cluster_similar(unique_sentences)

        # Step 4: Score and select best from each cluster
        claims = []
        for cluster in clusters:
            best = max(cluster, key=lambda s: self._score_sentence(s))
            direction = self._classify_direction(best)
            score = self._score_sentence(best)
            claims.append((best, direction, score))

        # Step 5: Sort by score and filter to budget
        claims.sort(key=lambda x: x[2], reverse=True)

        # Step 6: Build ultra-compact output
        compressed_text = self._build_ultra_compact(claims, token_budget)

        # Calculate metrics
        compressed_tokens = len(compressed_text.split())
        metrics = {
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(raw_tokens / compressed_tokens, 2) if compressed_tokens > 0 else 0,
            "claims_extracted": len(sentences),
            "claims_after_dedup": len(unique_sentences),
            "claims_after_clustering": len(clusters),
            "final_claims": len([c for c in claims if c[0] in compressed_text])
        }

        return compressed_text, metrics

    def _parse_sentences(self, evidence_chunks: List[Dict[str, Any]]) -> List[str]:
        """Parse all evidence into sentences"""
        sentences = []
        for chunk in evidence_chunks:
            text = chunk.get("text", "")
            # Split by punctuation
            raw_sents = re.split(r'[.!?]+', text)
            for sent in raw_sents:
                sent = sent.strip()
                if len(sent) > 15:  # Skip very short
                    # Remove filler words
                    sent = re.sub(r'\b(very|quite|really|extremely|the match was|showing|played)\b', '', sent, flags=re.IGNORECASE)
                    sent = re.sub(r'\s+', ' ', sent).strip()
                    if sent:
                        sentences.append(sent)
        return sentences

    def _cluster_similar(self, sentences: List[str]) -> List[List[str]]:
        """Cluster similar sentences"""
        clusters = []
        used = set()

        for i, sent1 in enumerate(sentences):
            if i in used:
                continue

            cluster = [sent1]
            used.add(i)
            tokens1 = set(sent1.lower().split())

            for j, sent2 in enumerate(sentences[i+1:], start=i+1):
                if j in used:
                    continue

                tokens2 = set(sent2.lower().split())
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)

                if overlap >= self.similarity_threshold:
                    cluster.append(sent2)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _score_sentence(self, sentence: str) -> float:
        """Score sentence by information value"""
        score = 0.0
        sent_lower = sentence.lower()

        # Has numbers
        if re.search(r'\d+', sentence):
            score += 0.4

        # Has signal words
        signal_count = sum(1 for word in self.YES_SIGNALS | self.NO_SIGNALS if word in sent_lower)
        score += min(signal_count * 0.2, 0.3)

        # Has named entities (capitalized words)
        if re.search(r'\b[A-Z][a-z]+', sentence):
            score += 0.2

        # Shorter is better (more dense)
        word_count = len(sentence.split())
        if word_count < 10:
            score += 0.1

        return min(score, 1.0)

    def _classify_direction(self, sentence: str) -> str:
        """Classify YES, NO, or NEUTRAL"""
        sent_lower = sentence.lower()
        sent_words = sent_lower.split()
        yes_count = sum(1 for word in self.YES_SIGNALS if word in sent_words)
        no_count = sum(1 for word in self.NO_SIGNALS if word in sent_words)

        if yes_count > no_count:
            return "YES"
        elif no_count > yes_count:
            return "NO"
        else:
            return "NEUTRAL"

    def _build_ultra_compact(self, claims: List[Tuple[str, str, float]], token_budget: int) -> str:
        """Build ultra-compact text output"""
        yes_claims = [(text, score) for text, dir, score in claims if dir == "YES"]
        no_claims = [(text, score) for text, dir, score in claims if dir == "NO"]

        lines = []
        tokens_used = 0

        # Add YES claims
        if yes_claims:
            yes_parts = []
            for text, score in yes_claims:
                # Shorten text aggressively
                short_text = text[:40]
                claim_str = f"{short_text}({score:.2f})"
                claim_tokens = len(claim_str.split())

                if tokens_used + claim_tokens <= token_budget:
                    yes_parts.append(claim_str)
                    tokens_used += claim_tokens
                else:
                    break

            if yes_parts:
                lines.append("YES:" + "|".join(yes_parts))

        # Add NO claims
        if no_claims:
            no_parts = []
            for text, score in no_claims:
                short_text = text[:40]
                claim_str = f"{short_text}({score:.2f})"
                claim_tokens = len(claim_str.split())

                if tokens_used + claim_tokens <= token_budget:
                    no_parts.append(claim_str)
                    tokens_used += claim_tokens
                else:
                    break

            if no_parts:
                lines.append("NO:" + "|".join(no_parts))

        return " ".join(lines)


# Test it
if __name__ == "__main__":
    compressor = UltraCompressor()

    evidence_chunks = [
        {
            "text": """France defeated Brazil 2-1 in a thrilling match.
                The match was very exciting. France beat Brazil 2-1.
                Mbappe scored twice. Mbappe was exceptional.
                However, France struggled in their last friendly.
                Pogba is injured. Pogba has an injury."""
        }
    ]

    compressed, metrics = compressor.compress(
        evidence_chunks,
        "Will France win?",
        token_budget=50
    )

    print(f"Input tokens: {metrics['raw_tokens']}")
    print(f"Output tokens: {metrics['compressed_tokens']}")
    print(f"Compression ratio: {metrics['compression_ratio']}x")
    print()
    print(f"Compressed output:")
    print(compressed)
