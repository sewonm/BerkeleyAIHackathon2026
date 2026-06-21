"""Decision agent — Claude-powered with heuristic fallback."""

import os
import re
import json
from typing import List

from app.schemas.decision import Decision
from app.schemas.market import Market

_SYSTEM_PROMPT = """You are a prediction market trading analyst. Given compressed evidence about a market question, decide whether to bet YES, NO, or HOLD.

Respond ONLY with a JSON object (no preamble, no code fences):
{
  "recommendation": "YES" | "NO" | "HOLD",
  "confidence": <float 0.0-1.0>,
  "fair_probability": <float 0.0-1.0>,
  "reasoning": "<2-3 sentence explanation>",
  "key_evidence": ["<evidence point 1>", "<evidence point 2>", "<evidence point 3>"],
  "missing_info": ["<gap 1>", "<gap 2>"]
}

Rules:
- YES if evidence strongly suggests the outcome will happen (fair_probability > market_yes_price + 0.05)
- NO if evidence strongly suggests it won't happen (fair_probability < market_yes_price - 0.05)
- HOLD if evidence is mixed, thin, or fair value is within 5 cents of market price
- confidence: how certain you are in your recommendation (not the probability of YES)
- fair_probability: your estimate of the true probability the market resolves YES
- key_evidence: 3 specific facts from the evidence that drove your decision
- missing_info: 2 things that would improve confidence if you knew them"""


class DecisionAgent:
    def __init__(self):
        self.name = "DecisionAgent"

    def run(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Decision:
        # Try Claude first
        try:
            return self._run_claude(market, compressed_context)
        except Exception:
            pass
        # Heuristic fallback
        return self._run_heuristic(market, compressed_context, kept_chunks)

    def _run_claude(self, market: Market, compressed_context: str) -> Decision:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("No ANTHROPIC_API_KEY")

        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        user_msg = (
            f"Market question: {market.question}\n"
            f"Current YES price: {market.current_yes_price:.2f} (i.e. market implies {market.current_yes_price*100:.0f}% chance)\n\n"
            f"Compressed evidence:\n{compressed_context[:4000]}"
        )

        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[
                {"role": "user", "content": f"{_SYSTEM_PROMPT}\n\n{user_msg}"}
            ],
        )

        raw = next((b.text for b in resp.content if hasattr(b, "text")), "")

        # Parse JSON — try direct, then strip fences, then regex
        data = None
        for attempt in [raw, re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")]:
            try:
                data = json.loads(attempt)
                break
            except Exception:
                pass
        if data is None:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))

        rec = data.get("recommendation", "HOLD")
        if rec not in ("YES", "NO", "HOLD"):
            rec = "HOLD"

        return Decision(
            recommendation=rec,
            confidence=round(float(data.get("confidence", 0.6)), 2),
            fair_probability=round(float(data.get("fair_probability", market.current_yes_price)), 2),
            reasoning=data.get("reasoning", ""),
            key_evidence=data.get("key_evidence", []),
            missing_info=data.get("missing_info", []),
        )

    def _run_heuristic(self, market: Market, compressed_context: str, kept_chunks: List[dict]) -> Decision:
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

        ctx = compressed_context.lower()
        pos = sum(1 for w in positive_signals if w in ctx)
        neg = sum(1 for w in negative_signals if w in ctx)
        strength = pos - neg

        key_evidence = []
        for chunk in kept_chunks[:5]:
            text = chunk.get("text", "") if isinstance(chunk, dict) else getattr(chunk, "text", "")
            if len(text) > 100:
                text = text[:97] + "..."
            key_evidence.append(text)

        if strength >= 3 and pos >= 5:
            rec, conf, fair = "YES", min(0.75 + strength * 0.03, 0.90), min(0.55 + strength * 0.02, 0.75)
            reasoning = f"Strong positive signals ({pos} indicators). Evidence suggests favorable outcome."
        elif strength <= -3 and neg >= 5:
            rec, conf, fair = "NO", min(0.70 + abs(strength) * 0.03, 0.85), max(0.30 - abs(strength) * 0.02, 0.20)
            reasoning = f"Strong negative signals ({neg} indicators). Evidence suggests unfavorable outcome."
        else:
            rec, conf, fair = "HOLD", 0.55, market.current_yes_price
            reasoning = f"Mixed signals (positive: {pos}, negative: {neg}). Insufficient evidence to take a position."

        return Decision(
            recommendation=rec,
            confidence=round(conf, 2),
            fair_probability=round(fair, 2),
            reasoning=reasoning,
            key_evidence=key_evidence or ["No high-signal evidence extracted."],
            missing_info=["Real-time market data", "Recent news updates"],
        )
