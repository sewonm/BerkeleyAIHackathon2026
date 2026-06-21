#!/usr/bin/env python3
"""
Web-search discovery demo — "scour a lot more".

Shows the keyless discovery layer turning a market into many query-driven raw
evidence chunks (Google News + DuckDuckGo + ESPN news), and the full merged
3-layer bundle (ESPN anchor + Browserbase noisy + search).

Usage:
    python scripts/validate_search.py                 # live (keyless)
    python scripts/validate_search.py "Will the Yankees win the World Series?"
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:  # load BROWSERBASE_* so the noisy layer can go live (optional)
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

from app.schemas.market import Market  # noqa: E402
from app.services.espn.registry import resolve_sport  # noqa: E402
from app.services.web_search import build_search_queries, collect_search_evidence  # noqa: E402
from app.services.sports_collector import collect_sports_evidence  # noqa: E402
from app.services.browserbase_service import BrowserbaseService  # noqa: E402

NOISY_FIX = REPO_ROOT / "tests" / "fixtures" / "noisy"

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "Will Argentina win the 2026 FIFA World Cup?"


def main() -> int:
    market = Market(
        market_id="demo", title=QUESTION, question=QUESTION,
        category="sports", resolution_criteria="Resolves on the official result.",
    )
    cfg = resolve_sport(market)

    print("=" * 70)
    print(" WEB-SEARCH DISCOVERY — scour a lot more")
    print("=" * 70)
    print(f"\nMarket: {QUESTION}\nSport:  {cfg.key} ({cfg.slug})")
    print("\nQueries built (entity x intent):")
    for q in build_search_queries(market, cfg):
        print(f"  • {q}")

    search = collect_search_evidence(market, sport_cfg=cfg)
    print(f"\nDiscovery chunks: {len(search)}")
    print("  by provider:", dict(Counter(c.metadata['provider'] for c in search)))
    print("\n  sample:")
    for c in search[:10]:
        print(f"   [{c.metadata['provider']:11s}] {c.text[:78]}")

    print("\n" + "-" * 70)
    print(" FULL MERGED BUNDLE (anchor + noisy + search)")
    print("-" * 70)
    bundle = collect_sports_evidence(
        market, sport=cfg.key,
        browserbase=BrowserbaseService(fixtures_dir=NOISY_FIX),  # fixtures fallback for noisy
    )
    print(f"Total chunks: {len(bundle)}")
    print("  by layer:", dict(Counter(c.metadata['fetched_via'] for c in bundle)))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
