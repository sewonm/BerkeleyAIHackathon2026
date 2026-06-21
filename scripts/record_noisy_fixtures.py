#!/usr/bin/env python3
"""
Record live Browserbase scrapes into tests/fixtures/noisy/ (raw text).

Requires a real Browserbase session to capture live data:
    export BROWSERBASE_API_KEY=...        # and BROWSERBASE_PROJECT_ID
    pip install -e ".[scrape]" && playwright install chromium
    python scripts/record_noisy_fixtures.py

Without a key / playwright, the noisy sources (Reddit, FBref, Sofascore,
Baseball-Reference) are anti-bot/JS and return nothing — the repo therefore ships
representative raw-text fixtures so the demo + tests run offline. This script
OVERWRITES those with real scrapes when a session is available.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.browserbase_service import BrowserbaseService  # noqa: E402
from app.services.espn.registry import SPORT_REGISTRY  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "noisy"
RECORD_SPORTS = ("soccer", "baseball")


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    # Write successful scrapes straight into the fixtures dir (cache == fixtures).
    service = BrowserbaseService(cache_dir=FIXTURES_DIR)

    if not service.has_live_capability:
        print(
            "No live Browserbase capability (need BROWSERBASE_API_KEY + playwright).\n"
            "Keeping the shipped representative fixtures in "
            f"{FIXTURES_DIR}."
        )

    recorded = 0
    for sport in RECORD_SPORTS:
        for target in SPORT_REGISTRY[sport].scrape_targets:
            text = service.scrape_text(target.url)
            status = f"{len(text)} chars" if text else "no live data (kept fixture)"
            print(f"  {sport:9s} {target.label:24s} -> {status}")
            if text:
                recorded += 1

    print(f"\nLive-recorded {recorded} target(s). Fixtures dir: {FIXTURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
