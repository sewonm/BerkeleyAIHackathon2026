"""Score evidence chunks for compression decisions"""

import re
from typing import List


# Culture-specific signal words that indicate relevant evidence
CULTURE_SIGNALS = {
    'streaming', 'box office', 'album', 'chart', 'award', 'trailer',
    'release', 'celebrity', 'trend', 'viral', 'viewership', 'audience',
    'poll', 'announcement', 'confirmed', 'rumor', 'official', 'deadline',
    'nomination', 'sales', 'debut', 'premiere', 'screening', 'festival',
    'critic', 'review', 'rating', 'score', 'winner', 'oscar', 'emmy',
    'grammy', 'golden globe', 'cannes', 'sundance', 'netflix', 'spotify',
    'billboard', 'record', 'ticket', 'million', 'billion'
}

# Evidence strength indicators
STRENGTH_INDICATORS = {
    'confirmed', 'official', 'announced', 'reported', 'verified',
    'according to', 'sources say', 'insider', 'exclusive', 'breaking',
    'statement', 'press release', 'data shows', 'statistics', 'study'
}

# Filler/boilerplate words that reduce relevance
FILLER_INDICATORS = {
    'meanwhile', 'however', 'additionally', 'furthermore', 'moreover',
    'in other news', 'unrelated', 'separately', 'aside from',
    'general', 'various', 'several', 'some', 'many', 'few'
}


class ChunkScorer:
    """
    Scores evidence chunks to determine which should be kept during compression.

    The scoring is transparent and interpretable, using simple heuristics:
    - Relevance to market question
    - Overlap with protected terms
    - Presence of culture signals
    - Presence of numbers/dates/proper nouns
    - Source strength indicators
    - Penalties for filler/boilerplate
    """

    def __init__(self, protected_terms: List[str]):
        """
        Initialize the scorer.

        Args:
            protected_terms: List of protected terms from the market
        """
        self.protected_terms = [term.lower() for term in protected_terms]

    def score(self, chunk_text: str, market_question: str) -> float:
        """
        Calculate a keep score for an evidence chunk.

        Score range: 0.0 to 1.0 (higher = more likely to keep)

        Args:
            chunk_text: The text of the evidence chunk
            market_question: The market question

        Returns:
            Keep score between 0 and 1
        """
        chunk_lower = chunk_text.lower()
        question_lower = market_question.lower()

        score = 0.0

        # 1. Relevance to market question (max +0.30)
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        chunk_words = set(re.findall(r'\b\w+\b', chunk_lower))
        overlap = question_words & chunk_words
        relevance_score = min(len(overlap) / max(len(question_words), 1) * 0.30, 0.30)
        score += relevance_score

        # 2. Protected terms overlap (max +0.25)
        protected_matches = sum(1 for term in self.protected_terms if term in chunk_lower)
        protected_score = min(protected_matches * 0.10, 0.25)
        score += protected_score

        # 3. Culture signal words (max +0.20)
        culture_matches = sum(1 for signal in CULTURE_SIGNALS if signal in chunk_lower)
        culture_score = min(culture_matches * 0.05, 0.20)
        score += culture_score

        # 4. Numbers, dates, prices (max +0.15)
        has_numbers = bool(re.search(r'\b\d+\b', chunk_text))
        has_dates = bool(re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|\d{4})\b', chunk_lower))
        has_prices = bool(re.search(r'\$\d+', chunk_text))

        if has_numbers:
            score += 0.07
        if has_dates:
            score += 0.05
        if has_prices:
            score += 0.03

        # 5. Source strength indicators (max +0.10)
        strength_matches = sum(1 for indicator in STRENGTH_INDICATORS if indicator in chunk_lower)
        strength_score = min(strength_matches * 0.05, 0.10)
        score += strength_score

        # 6. Proper nouns (capitalized words) (max +0.10)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', chunk_text)
        proper_noun_score = min(len(proper_nouns) * 0.02, 0.10)
        score += proper_noun_score

        # 7. Penalties for filler/boilerplate (max -0.20)
        filler_matches = sum(1 for filler in FILLER_INDICATORS if filler in chunk_lower)
        filler_penalty = min(filler_matches * 0.05, 0.20)
        score -= filler_penalty

        # 8. Penalty for very short chunks (likely incomplete)
        if len(chunk_text.split()) < 10:
            score -= 0.10

        # 9. Penalty for very generic text (low unique word ratio)
        unique_words = len(set(chunk_lower.split()))
        total_words = len(chunk_lower.split())
        if total_words > 0:
            uniqueness_ratio = unique_words / total_words
            if uniqueness_ratio < 0.4:  # Very repetitive text
                score -= 0.10

        # Clamp score to [0, 1]
        score = max(0.0, min(1.0, score))

        return score

    def score_batch(self, chunks: List[str], market_question: str) -> List[float]:
        """
        Score multiple chunks at once.

        Args:
            chunks: List of chunk texts
            market_question: The market question

        Returns:
            List of scores corresponding to each chunk
        """
        return [self.score(chunk, market_question) for chunk in chunks]
