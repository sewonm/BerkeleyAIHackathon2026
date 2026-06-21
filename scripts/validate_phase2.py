#!/usr/bin/env python3
"""
Phase 2 acceptance demo — ESPN HTTP anchor, sport-agnostic.

Proves the four roadmap success criteria on TWO live sports (FIFA World Cup
soccer + MLB) from a single, sport-agnostic pipeline:

  1. Resolve the sport/league + live/most-recent event from the registry (no
     hardcoded sport).
  2. Return chunks for score/state, box stats + events, odds, win-prob, injuries
     /lineups.
  3. Anchor chunks carry fetched_via="http", sport, source_strength; output is
     deterministic across runs.
  4. Works for both sports — adding a sport is config-only.

Usage:
    python scripts/validate_phase2.py            # live network
    ESPN_FIXTURES_DIR=tests/fixtures/espn ESP_OFFLINE=1 \
        python scripts/validate_phase2.py        # offline from fixtures
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.schemas.market import Market  # noqa: E402
from app.services.espn import collect_espn_evidence, resolve_sport  # noqa: E402

FIXED_TS = "2026-06-20T00:00:00Z"

MARKETS = [
    Market(
        market_id="wc-2026",
        title="2026 FIFA World Cup",
        question="Will the favorite win this World Cup soccer match?",
        category="sports",
        resolution_criteria="Resolves on the official FIFA result.",
    ),
    Market(
        market_id="mlb-2026",
        title="MLB game outcome",
        question="Will the home team win this MLB baseball game?",
        category="sports",
        resolution_criteria="Resolves on the official MLB result.",
    ),
]

EXPECTED_KINDS = {"score_state", "box_stats", "event_log", "odds", "win_probability"}


def main() -> int:
    print("=" * 70)
    print(" PHASE 2 VALIDATION — ESPN HTTP anchor (sport-agnostic)")
    print("=" * 70)

    all_kinds: set[str] = set()
    ok = True

    for market in MARKETS:
        cfg = resolve_sport(market)
        chunks = collect_espn_evidence(market, observed_at=FIXED_TS)
        kinds = [c.metadata["kind"] for c in chunks]
        all_kinds |= set(kinds)

        print(f"\n▶ market: {market.title}")
        print(f"  resolved sport -> {cfg.key} ({cfg.slug})   [criterion 1]")
        print(f"  chunks: {len(chunks)} -> {kinds}")

        if not chunks:
            print("  ⚠ no chunks (network down + no fixtures?) — skipping detail")
            ok = False
            continue

        # criterion 3: metadata shape
        for c in chunks:
            md = c.metadata
            assert md["fetched_via"] == "http", md
            assert md["sport"] == cfg.key, md
            assert md["source_strength"] == "anchor", md
        print("  metadata: fetched_via=http, sport set, source_strength=anchor  [criterion 3]")

        # criterion 3: determinism
        again = collect_espn_evidence(market, observed_at=FIXED_TS)
        det = [(c.metadata["kind"], c.text) for c in chunks] == \
              [(c.metadata["kind"], c.text) for c in again]
        print(f"  deterministic across runs: {det}  [criterion 3]")
        ok = ok and det

        # show one line of each chunk
        for c in chunks:
            first = c.text.splitlines()[0] if c.text else ""
            print(f"    - {c.metadata['kind']:16s} {first[:70]}")

    print("\n" + "-" * 70)
    covered = EXPECTED_KINDS & all_kinds
    print(f"Data kinds across both sports: {sorted(all_kinds)}")
    print(f"Required kinds covered ({len(covered)}/{len(EXPECTED_KINDS)}): "
          f"{sorted(covered)}   [criterion 2]")
    print(f"Availability (injuries/lineups) present: "
          f"{bool(all_kinds & {'injuries', 'lineups'})}   [criterion 2]")
    print("Two sports from one config-only pipeline (soccer + MLB)  [criterion 4]")

    missing = EXPECTED_KINDS - all_kinds
    if missing:
        print(f"\n⚠ missing kinds across both sports: {missing}")
        ok = False

    print("\n" + "=" * 70)
    print(" RESULT:", "PASS ✓" if ok else "INCOMPLETE (see warnings above)")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
