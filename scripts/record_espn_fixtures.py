#!/usr/bin/env python3
"""
Record live ESPN responses into tests/fixtures/espn/ for deterministic, offline
tests and a network-free demo path.

Run from the repo root with live network:
    python scripts/record_espn_fixtures.py

Re-run to refresh fixtures (e.g. when a new game is live). The same code path that
records also reads the fixtures back, so resolution stays self-consistent: the
recorded scoreboard resolves to the same event whose summary/odds were recorded.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.schemas.market import Market  # noqa: E402
from app.services.espn import ESPNClient, collect_espn_evidence  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "espn"

# Sports we ship fixtures for (the two validated live sports).
RECORD_SPORTS = ("soccer", "baseball")

# Fixed timestamp so recorded-vs-replayed chunk text is byte-stable.
FIXED_OBSERVED_AT = "2026-06-20T00:00:00Z"


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    client = ESPNClient(record_dir=FIXTURES_DIR)  # live network + record

    total = 0
    for sport in RECORD_SPORTS:
        market = Market(
            market_id=f"rec-{sport}",
            title=f"record {sport}",
            question=f"record {sport}",
            category="sports",
            resolution_criteria="n/a",
        )
        chunks = collect_espn_evidence(
            market, client=client, sport=sport, observed_at=FIXED_OBSERVED_AT
        )
        kinds = [c.metadata["kind"] for c in chunks]
        print(f"  {sport:9s}: {len(chunks)} chunks -> {kinds}")
        total += len(chunks)

    files = sorted(p.name for p in FIXTURES_DIR.glob("*.json"))
    print(f"\nRecorded {len(files)} fixture file(s) into {FIXTURES_DIR}:")
    for f in files:
        print(f"  - {f}")

    if total == 0:
        print("\nWARNING: recorded 0 chunks — is the network up / are games scheduled?")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
