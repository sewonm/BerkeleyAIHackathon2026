"""Decision agent - Claude LLM primary, keyword-count fallback"""

import os
import re
from typing import List, Optional

from app.schemas.decision import Decision
from app.schemas.market import Market


class DecisionAgent:
    """Makes trading decisions from compressed evidence using Claude (keyword fallback)."""

    def __init__(self):
        self.name = "DecisionAgent"
        self.description = "Makes trading decisions from compressed evidence"

    def run(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Decision:
        llm_result = self._try_llm(market, compressed_context, kept_chunks)
        if llm_result is not None:
            return llm_result
        return self._keyword_decision(market, compressed_context, kept_chunks)

    def _try_llm(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Optional[Decision]:
        """Call Claude for a structured decision. Returns None on any failure."""
        try:
            _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from dotenv import load_dotenv
            load_dotenv(os.path.join(_root, '.env'))

            from app.services.llm_service import LLMService
            llm = LLMService()
            if not llm.available:
                return None

            system = (
                "You are a prediction market analyst. Analyze the evidence and return ONLY a JSON object.\n\n"
                'Required format:\n{"recommendation": "YES"|"NO"|"HOLD", "confidence": 0.0-1.0, '
                '"fair_probability": 0.0-1.0, "reasoning": "...", '
                '"key_evidence": ["..."], "missing_info": ["..."]}\n\n'
                "Rules:\n"
                "- YES if fair_probability > 0.60 and evidence is strong\n"
                "- NO if fair_probability < 0.35 and evidence is strong\n"
                "- HOLD if mixed signals or probability between 0.35 and 0.60\n"
                "- confidence = certainty in your recommendation (not the probability)\n"
                "- reasoning: 1-3 concise sentences"
            )
            evidence_lines = '\n'.join(
                f"- {c.get('text', '')[:200]}" for c in kept_chunks[:8]
            )
            user = (
                f"Market: {market.question}\n\n"
                f"Compressed Evidence:\n{compressed_context[:3000]}\n\n"
                f"Top Evidence Chunks:\n{evidence_lines}"
            )

            result = llm.chat_json(system, user)
            if not result.ok:
                return None

            d = result.data
            rec = str(d.get('recommendation', 'HOLD')).upper()
            if rec not in ('YES', 'NO', 'HOLD'):
                rec = 'HOLD'

            return Decision(
                recommendation=rec,
                confidence=round(min(max(float(d.get('confidence', 0.5)), 0.0), 1.0), 2),
                fair_probability=round(min(max(float(d.get('fair_probability', 0.5)), 0.0), 1.0), 2),
                reasoning=str(d.get('reasoning', 'LLM decision')),
                key_evidence=[str(e) for e in (d.get('key_evidence') or [])[:5]],
                missing_info=[str(m) for m in (d.get('missing_info') or [])[:4]],
            )
        except Exception:
            return None

    def _keyword_decision(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Decision:
        """Fallback: deterministic keyword signal counting."""
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

        context_lower = compressed_context.lower()
        positive_count = sum(1 for w in positive_signals if w in context_lower)
        negative_count = sum(1 for w in negative_signals if w in context_lower)
        neutral_count = sum(1 for w in neutral_signals if w in context_lower)
        has_numbers = bool(re.search(r'\d+', compressed_context))
        has_dates = bool(re.search(
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december|\d{4})\b',
            context_lower
        ))

        signal_strength = positive_count - negative_count
        total_signals = positive_count + negative_count + neutral_count

        key_evidence = []
        for chunk in kept_chunks[:5]:
            text = chunk.get('text', '')
            if len(text) > 100:
                text = text[:97] + "..."
            key_evidence.append(text)

        if signal_strength >= 3 and positive_count >= 5:
            recommendation = "YES"
            confidence = min(0.75 + (signal_strength * 0.03), 0.90)
            fair_probability = min(0.55 + (signal_strength * 0.02), 0.75)
            reasoning = f"Strong positive signals ({positive_count} indicators). Evidence suggests favorable outcome."
        elif signal_strength <= -3 and negative_count >= 5:
            recommendation = "NO"
            confidence = min(0.70 + (abs(signal_strength) * 0.03), 0.85)
            fair_probability = max(0.30 - (abs(signal_strength) * 0.02), 0.20)
            reasoning = f"Strong negative signals ({negative_count} indicators). Evidence suggests unfavorable outcome."
        else:
            recommendation = "HOLD"
            confidence = 0.50 + (total_signals * 0.01)
            fair_probability = 0.45 + (signal_strength * 0.02)
            reasoning = f"Mixed signals (positive: {positive_count}, negative: {negative_count}). More evidence needed."

        if has_numbers:
            confidence += 0.05
        if has_dates:
            confidence += 0.05
        confidence = min(confidence, 0.95)

        return Decision(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            fair_probability=round(fair_probability, 2) if fair_probability else None,
            reasoning=reasoning,
            key_evidence=key_evidence,
            missing_info=["Real-time market data", "Recent news updates", "Expert analysis", "Historical precedent data"],
        )
