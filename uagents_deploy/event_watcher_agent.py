"""
EventWatcher — live news trigger agent for SignalForge.

Polls Google News RSS every 2 minutes for breaking sports/entertainment events.
When a trigger is detected (injury, suspension, elimination, etc.), it:
  1. Uses Claude to auto-generate a prediction market question
  2. Runs the full SignalForge pipeline (evidence → compress → decide)
  3. Logs a dry-run Kalshi trade to Redis if confidence >= 0.70

Run standalone:
  python uagents_deploy/event_watcher_agent.py

Or import and call:
  from event_watcher_agent import EventWatcher
  EventWatcher().scan_once()
"""

import hashlib
import os
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

import httpx

# ── Path setup ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# ── Config ────────────────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 120
CONFIDENCE_THRESHOLD = 0.70

WATCH_QUERIES = [
    "world cup 2026 player injury",
    "world cup 2026 player suspended",
    "FIFA 2026 player out",
    "NBA 2026 player injured",
    "sports injury suspended 2026",
]

TRIGGER_KEYWORDS = [
    "injur", "sidelined", "out for", "suspended", "suspension",
    "banned", "eliminated", "traded", "fired", "resigned",
    "withdrew", "retirement", "retires", "out with",
]

SEEN_KEY = "watcher:seen_headlines"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _headline_hash(title: str) -> str:
    return hashlib.md5(title.lower().strip().encode()).hexdigest()[:12]


def _is_trigger(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TRIGGER_KEYWORDS)


def _fetch_rss(query: str) -> list:
    """Return list of headline dicts from Google News RSS for a query."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SignalForge-Watcher/1.0)"},
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "").strip()
            pub = item.findtext("pubDate", "").strip()
            src = item.find("source")
            source_name = src.text if src is not None else ""
            if title:
                items.append({"title": title, "pub_date": pub, "source": source_name})
        return items
    except Exception:
        return []


def _generate_market_question(headline: str) -> Optional[dict]:
    """Use Claude to turn a news headline into a structured market question dict."""
    try:
        from app.services.llm_service import LLMService
        llm = LLMService()
        if not llm.available:
            return None
        result = llm.chat_json(
            system=(
                "You are a prediction market designer. Given a breaking news headline, "
                "generate a single YES/NO prediction market question traders can bet on. "
                "The question must be specific, answerable, and directly tied to the headline. "
                'Return ONLY JSON: {"question": "Will ...", '
                '"category": "sports|politics|culture|finance", '
                '"protected_terms": ["term1", "term2"]}'
            ),
            user=f"Breaking news headline: {headline}",
        )
        if result.ok and "question" in result.data:
            return result.data
    except Exception:
        pass
    return None


def _run_pipeline(market_id: str, question: str, category: str, protected_terms: list) -> Optional[dict]:
    """Run the full SignalForge pipeline and return the result dict."""
    try:
        from app.schemas.market import Market
        from app.agents.coordinator import Coordinator

        market = Market(
            market_id=market_id,
            title=question[:120],
            question=question,
            category=category,
            resolution_criteria=f"Resolves based on: {question}",
            protected_terms=protected_terms,
        )
        return Coordinator().run(market)
    except Exception as e:
        print(f"[EventWatcher] Pipeline error: {type(e).__name__}: {e}")
        return None


# ── EventWatcher ──────────────────────────────────────────────────────────────

class EventWatcher:
    """Polls Google News RSS for trigger events and fires the SignalForge pipeline."""

    def _redis(self):
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            return redis.from_url(url, decode_responses=True)
        except Exception:
            return None

    def _already_seen(self, headline: str) -> bool:
        r = self._redis()
        return bool(r and r.sismember(SEEN_KEY, _headline_hash(headline)))

    def _mark_seen(self, headline: str):
        r = self._redis()
        if r:
            r.sadd(SEEN_KEY, _headline_hash(headline))

    def _log_dry_run(self, market_id: str, question: str, decision, headline: str):
        try:
            from app.services.kalshi_dry_run import log_dry_run_trade
            trade = log_dry_run_trade(market_id, question, decision, headline)
            print(
                f"[EventWatcher] Dry-run: {trade['action']} "
                f"(conf={decision.confidence:.0%}, prob={decision.fair_probability})"
            )
        except Exception as e:
            print(f"[EventWatcher] Dry-run log error: {e}")

    def scan_once(self) -> list:
        """
        Run one full scan across all watch queries.
        Returns list of triggered event dicts.
        """
        triggered = []
        seen_this_scan: set = set()  # dedup within a single scan pass

        for query in WATCH_QUERIES:
            items = _fetch_rss(query)
            for item in items:
                headline = item["title"]
                h = _headline_hash(headline)

                if h in seen_this_scan:
                    continue
                if not _is_trigger(headline):
                    continue
                if self._already_seen(headline):
                    continue

                seen_this_scan.add(h)
                self._mark_seen(headline)

                print(f"\n[EventWatcher] TRIGGER: {headline}")
                print(f"  Source: {item.get('source', '?')}  |  {item.get('pub_date', '')[:25]}")

                # Generate market question via Claude
                q_data = _generate_market_question(headline)
                if q_data:
                    question = q_data.get("question", headline)
                    category = q_data.get("category", "sports")
                    protected_terms = q_data.get("protected_terms", [])
                else:
                    question = f"Will this event resolve favorably? [{headline[:80]}]"
                    category = "sports"
                    protected_terms = []

                market_id = f"event-{h}"
                print(f"[EventWatcher] Market: {question}")

                # Run full pipeline
                result = _run_pipeline(market_id, question, category, protected_terms)
                if not result:
                    continue

                decision = result["decision"]
                print(
                    f"[EventWatcher] → {decision.recommendation} "
                    f"| conf={decision.confidence:.0%} | p(YES)={decision.fair_probability}"
                )

                # Log dry-run trade if actionable
                if decision.recommendation != "HOLD" and decision.confidence >= CONFIDENCE_THRESHOLD:
                    self._log_dry_run(market_id, question, decision, headline)

                triggered.append({
                    "headline": headline,
                    "source": item.get("source", ""),
                    "pub_date": item.get("pub_date", ""),
                    "market_id": market_id,
                    "question": question,
                    "recommendation": decision.recommendation,
                    "confidence": decision.confidence,
                    "fair_probability": decision.fair_probability,
                    "reasoning": decision.reasoning,
                    "timestamp": _utc_now(),
                })

        return triggered

    def watch(self):
        """Continuous polling loop. Ctrl+C to stop."""
        print(f"[EventWatcher] Live event watch started (interval={POLL_INTERVAL_SECONDS}s)")
        print(f"[EventWatcher] Watching {len(WATCH_QUERIES)} query streams:")
        for q in WATCH_QUERIES:
            print(f"  · {q}")
        print()

        while True:
            try:
                print(f"[EventWatcher] Scanning at {_utc_now()} ...")
                triggered = self.scan_once()
                if triggered:
                    print(f"[EventWatcher] {len(triggered)} event(s) processed this scan.")
                else:
                    print(f"[EventWatcher] No new triggers. Next scan in {POLL_INTERVAL_SECONDS}s.")
            except KeyboardInterrupt:
                print("\n[EventWatcher] Stopped.")
                break
            except Exception as e:
                print(f"[EventWatcher] Scan error: {type(e).__name__}: {e}")

            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    EventWatcher().watch()
