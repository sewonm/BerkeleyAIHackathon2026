"""
Claim extractors for the compression pipeline.

Includes:
- Heuristic extractor (fallback)
- Claude-based extractor (primary)
"""

import re
import json
import os
from typing import List, Tuple, Optional
from datetime import datetime

from app.compression.schemas_advanced import ExtractedClaim, EnhancedEvidenceChunk


# ============================================================================
# Signal Words and Patterns
# ============================================================================

SIGNAL_WORDS = {
    "confirmed", "official", "announced", "reported", "wins", "loses",
    "leads", "trails", "injury", "questionable", "out", "poll",
    "nomination", "award", "box office", "revenue", "inflation", "rate",
    "earnings", "price", "odds", "probability", "deadline", "ruling",
    "lawsuit", "trend", "viral", "market", "volume", "liquidity",
    "expected", "predicted", "forecast", "likely", "unlikely",
    "approval", "rejection", "passed", "failed", "winning", "losing"
}

YES_SIGNALS = {
    "wins", "winning", "leads", "leading", "frontrunner", "favorite",
    "approved", "passed", "nominated", "awarded", "confirmed", "yes",
    "positive", "growth", "increase", "gains", "surging", "momentum"
}

NO_SIGNALS = {
    "loses", "losing", "trails", "trailing", "underdog", "unlikely",
    "rejected", "failed", "denied", "no", "negative", "decline",
    "decrease", "losses", "falling", "slump", "controversy"
}

FILLER_WORDS = {
    "meanwhile", "however", "additionally", "furthermore", "moreover",
    "in other news", "unrelated", "separately", "aside from",
    "general", "various", "several", "some", "many", "few"
}


# ============================================================================
# Heuristic Claim Extractor
# ============================================================================

class HeuristicClaimExtractor:
    """
    Fallback claim extractor using heuristics.

    This runs when Claude is unavailable or fails.
    """

    def __init__(self):
        self.signal_words = SIGNAL_WORDS
        self.yes_signals = YES_SIGNALS
        self.no_signals = NO_SIGNALS
        self.filler_words = FILLER_WORDS

    def extract_claims(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        """
        Extract claims using heuristics.

        Args:
            chunk: Evidence chunk
            market_question: Market question
            resolution_criteria: Resolution criteria

        Returns:
            List of extracted claims
        """
        claims = []

        # Split into sentences
        sentences = self._split_sentences(chunk.text)

        for sentence in sentences:
            # Check if sentence is relevant
            if not self._is_relevant(sentence, market_question):
                continue

            # Extract entities, dates, numbers
            entities = self._extract_entities(sentence)
            dates = self._extract_dates(sentence)
            numbers = self._extract_numbers(sentence)

            # Classify direction
            direction = self._classify_direction(sentence)

            # Calculate scores
            confidence = self._calculate_confidence(sentence, entities, dates, numbers)
            market_impact = self._calculate_market_impact(sentence, direction)

            # Create claim
            claim = ExtractedClaim(
                claim_text=sentence,
                canonical_text=sentence.lower().strip(),
                source_chunk_id=chunk.chunk_id,
                source_agent=chunk.source_agent,
                entities=entities,
                dates=dates,
                numbers=numbers,
                direction=direction,
                confidence=confidence,
                market_impact_score=market_impact,
                estimated_probability_shift=self._estimate_prob_shift(market_impact, direction),
                reason=f"Heuristic extraction from {chunk.source_agent}",
                extraction_method="heuristic"
            )

            claims.append(claim)

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _is_relevant(self, sentence: str, market_question: str) -> bool:
        """Check if sentence is relevant to the market"""
        sentence_lower = sentence.lower()

        # Check for signal words
        has_signal = any(word in sentence_lower for word in self.signal_words)

        # Check for numbers or dates
        has_data = bool(re.search(r'\d+', sentence))

        # Check for named entities (capitalized words)
        has_entities = bool(re.search(r'\b[A-Z][a-z]+\b', sentence))

        # Check for filler words (negative signal)
        has_filler = any(word in sentence_lower for word in self.filler_words)

        # Relevant if has signals and not mostly filler
        return (has_signal or has_data or has_entities) and not has_filler

    def _extract_entities(self, sentence: str) -> List[str]:
        """Extract named entities (simple heuristic)"""
        # Find sequences of capitalized words
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
        return list(set(entities))

    def _extract_dates(self, sentence: str) -> List[str]:
        """Extract dates"""
        dates = []

        # Month names
        months = re.findall(
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
            sentence
        )
        dates.extend(months)

        # Years
        years = re.findall(r'\b(20\d{2})\b', sentence)
        dates.extend(years)

        return list(set(dates))

    def _extract_numbers(self, sentence: str) -> List[str]:
        """Extract numbers"""
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', sentence)
        return numbers

    def _classify_direction(self, sentence: str) -> str:
        """Classify if claim supports YES, NO, or NEUTRAL"""
        sentence_lower = sentence.lower()

        yes_count = sum(1 for word in self.yes_signals if word in sentence_lower)
        no_count = sum(1 for word in self.no_signals if word in sentence_lower)

        if yes_count > no_count and yes_count >= 1:
            return "YES"
        elif no_count > yes_count and no_count >= 1:
            return "NO"
        else:
            return "NEUTRAL"

    def _calculate_confidence(
        self,
        sentence: str,
        entities: List[str],
        dates: List[str],
        numbers: List[str]
    ) -> float:
        """Calculate confidence score"""
        score = 0.3  # Base score

        # Boost for data
        if entities:
            score += 0.15
        if dates:
            score += 0.15
        if numbers:
            score += 0.15

        # Boost for signal words
        sentence_lower = sentence.lower()
        signal_count = sum(1 for word in self.signal_words if word in sentence_lower)
        score += min(signal_count * 0.05, 0.25)

        return min(score, 0.95)

    def _calculate_market_impact(self, sentence: str, direction: str) -> float:
        """Calculate market impact score"""
        if direction == "NEUTRAL":
            return 0.3

        sentence_lower = sentence.lower()

        # Base impact
        impact = 0.5

        # Boost for strong signals
        if "confirmed" in sentence_lower or "official" in sentence_lower:
            impact += 0.2

        # Boost for numbers
        if re.search(r'\d+', sentence):
            impact += 0.1

        return min(impact, 0.95)

    def _estimate_prob_shift(self, market_impact: float, direction: str) -> float:
        """Estimate probability shift"""
        if direction == "NEUTRAL":
            return 0.0

        # Shift proportional to market impact
        shift = market_impact * 0.15

        if direction == "NO":
            shift = -shift

        return shift


# ============================================================================
# Claude-based Claim Extractor
# ============================================================================

class ClaudeClaimExtractor:
    """
    Claude-based claim extractor using Anthropic SDK.

    Falls back to heuristic extractor on failure.
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.heuristic_fallback = HeuristicClaimExtractor()

        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                print("[ClaudeExtractor] Warning: anthropic package not installed")
                self.client = None
        else:
            print("[ClaudeExtractor] No ANTHROPIC_API_KEY found, will use heuristic fallback")

    def extract_claims(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> Tuple[List[ExtractedClaim], str]:
        """
        Extract claims using Claude or fallback.

        Returns:
            (claims, method_used)
        """
        if not self.client:
            claims = self.heuristic_fallback.extract_claims(chunk, market_question, resolution_criteria)
            return claims, "heuristic_fallback"

        try:
            claims = self._extract_with_claude(chunk, market_question, resolution_criteria)
            return claims, "claude"
        except Exception as e:
            print(f"[ClaudeExtractor] Claude extraction failed: {e}, using fallback")
            claims = self.heuristic_fallback.extract_claims(chunk, market_question, resolution_criteria)
            return claims, "heuristic_fallback"

    def _extract_with_claude(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        """Extract claims using Claude API"""
        prompt = self._build_prompt(chunk, market_question, resolution_criteria)

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",  # Fast and cheap for extraction
            max_tokens=2000,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text

        # Parse JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from Claude response")

        # Convert to ExtractedClaim objects
        claims = []
        for claim_data in data.get("claims", []):
            claim = ExtractedClaim(
                claim_text=claim_data.get("claim_text", ""),
                canonical_text=claim_data.get("canonical_text", claim_data.get("claim_text", "")),
                source_chunk_id=chunk.chunk_id,
                source_agent=chunk.source_agent,
                entities=claim_data.get("entities", []),
                dates=claim_data.get("dates", []),
                numbers=claim_data.get("numbers", []),
                direction=claim_data.get("direction", "NEUTRAL"),
                confidence=claim_data.get("confidence", 0.5),
                market_impact_score=claim_data.get("market_impact_score", 0.0),
                estimated_probability_shift=claim_data.get("estimated_probability_shift", 0.0),
                reason=claim_data.get("reason", ""),
                extraction_method="claude"
            )
            claims.append(claim)

        return claims

    def _build_prompt(
        self,
        chunk: EnhancedEvidenceChunk,
        market_question: str,
        resolution_criteria: str
    ) -> str:
        """Build the Claude prompt"""
        return f"""You are extracting structured prediction-market evidence.

Market question:
{market_question}

Resolution criteria:
{resolution_criteria}

Evidence chunk:
{chunk.text}

Extract concise structured claims that could affect whether the market resolves YES or NO.

Return valid JSON only:

{{
  "claims": [
    {{
      "claim_text": "...",
      "canonical_text": "...",
      "entities": ["..."],
      "dates": ["..."],
      "numbers": ["..."],
      "direction": "YES | NO | NEUTRAL",
      "confidence": 0.0,
      "market_impact_score": 0.0,
      "estimated_probability_shift": 0.0,
      "reason": "..."
    }}
  ],
  "missing_info": ["..."],
  "contradiction_hints": ["..."]
}}

Rules:
- Do not include irrelevant filler.
- Preserve important names, dates, numbers, prices, odds, deadlines, and official statements.
- Direction means whether the claim supports YES, supports NO, or is unclear.
- market_impact_score should reflect decision relevance (0.0 to 1.0).
- estimated_probability_shift should usually be between -0.15 and 0.15.
- Return JSON only, no other text.
"""
