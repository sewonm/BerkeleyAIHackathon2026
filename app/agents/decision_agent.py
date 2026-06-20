"""Decision agent - Simple deterministic implementation for MVP"""

import re
from typing import List

from app.schemas.decision import Decision
from app.schemas.market import Market


class DecisionAgent:
    """
    Agent that makes trading decisions based on compressed evidence.

    For MVP, this uses a simple deterministic rule-based approach.
    In production, this would use an LLM to analyze the compressed context.

    The agent outputs:
    - YES / NO / HOLD recommendation
    - Confidence score
    - Fair probability estimate
    - Reasoning
    - Key evidence
    - Missing information
    """

    def __init__(self):
        self.name = "DecisionAgent"
        self.description = "Makes trading decisions from compressed evidence"

    def run(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Decision:
        """
        Make a decision based on the compressed evidence.

        For MVP, uses simple heuristics:
        - Look for positive/negative signal words
        - Count evidence strength indicators
        - Default to HOLD unless there's strong evidence

        Args:
            market: The market being analyzed
            compressed_context: The compressed evidence text
            kept_chunks: The chunks that were kept with scores

        Returns:
            Decision object with recommendation and reasoning
        """
        # Simple sentiment analysis
        positive_signals = [
            'nomination', 'nominated', 'award', 'winner', 'won', 'leading',
            'frontrunner', 'favorite', 'strong', 'likely', 'expected',
            'confirmed', 'official', 'announced', 'success', 'acclaimed',
            'critic', 'praise', 'top', 'best', 'first', 'record'
        ]

        negative_signals = [
            'lost', 'failed', 'unlikely', 'weak', 'poor', 'criticism',
            'controversy', 'denied', 'rejected', 'cancelled', 'postponed',
            'doubt', 'question', 'uncertain', 'rumor'
        ]

        neutral_signals = [
            'maybe', 'possibly', 'unclear', 'unknown', 'unconfirmed',
            'speculation', 'potential'
        ]

        # Count signals in the compressed context
        context_lower = compressed_context.lower()

        positive_count = sum(1 for word in positive_signals if word in context_lower)
        negative_count = sum(1 for word in negative_signals if word in context_lower)
        neutral_count = sum(1 for word in neutral_signals if word in context_lower)

        # Look for numbers and dates (usually increase confidence)
        has_numbers = bool(re.search(r'\d+', compressed_context))
        has_dates = bool(re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|\d{4})\b', context_lower))

        # Calculate signal strength
        signal_strength = positive_count - negative_count
        total_signals = positive_count + negative_count + neutral_count

        # Extract key evidence (top scored chunks)
        key_evidence = []
        for chunk in kept_chunks[:5]:  # Top 5 chunks
            text = chunk.get('text', '')
            if len(text) > 100:
                text = text[:97] + "..."
            key_evidence.append(text)

        # Determine recommendation
        if signal_strength >= 3 and positive_count >= 5:
            recommendation = "YES"
            confidence = min(0.75 + (signal_strength * 0.03), 0.90)
            fair_probability = min(0.55 + (signal_strength * 0.02), 0.75)
            reasoning = f"Strong positive signals detected ({positive_count} positive indicators). Evidence suggests favorable outcome."
        elif signal_strength <= -3 and negative_count >= 5:
            recommendation = "NO"
            confidence = min(0.70 + (abs(signal_strength) * 0.03), 0.85)
            fair_probability = max(0.30 - (abs(signal_strength) * 0.02), 0.20)
            reasoning = f"Strong negative signals detected ({negative_count} negative indicators). Evidence suggests unfavorable outcome."
        else:
            recommendation = "HOLD"
            confidence = 0.50 + (total_signals * 0.01)
            fair_probability = 0.45 + (signal_strength * 0.02)
            reasoning = f"Mixed or insufficient signals (positive: {positive_count}, negative: {negative_count}). More evidence needed."

        # Adjust confidence based on data quality
        if has_numbers:
            confidence += 0.05
        if has_dates:
            confidence += 0.05

        # Cap confidence
        confidence = min(confidence, 0.95)

        # Missing information (placeholder)
        missing_info = [
            "Real-time market data",
            "Recent news updates",
            "Expert analysis",
            "Historical precedent data"
        ]

        return Decision(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            fair_probability=round(fair_probability, 2) if fair_probability else None,
            reasoning=reasoning,
            key_evidence=key_evidence,
            missing_info=missing_info
        )
