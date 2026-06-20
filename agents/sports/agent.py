"""
Sports research agent.

Responsibility: fetch live odds, line movement, and injury notes for a sports
event and emit a ResearchOutput. No LLM reasoning here.

Run standalone:
    python agents/sports/agent.py KXNBA-25DEC25-LAKERS "Lakers vs Celtics"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from schemas.schema import ResearchOutput, SportsEvidence


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_odds(event_hint: str) -> dict:
    # TODO: replace with real TheOddsAPI call
    # GET https://api.the-odds-api.com/v4/sports/{sport}/odds
    # params = {"apiKey": os.getenv("ODDS_API_KEY"), "regions": "us", "markets": "h2h,spreads"}
    return {
        "event_name": event_hint or "Team A vs Team B",
        "odds_snapshot": "Team A -110 / Team B +100",
        "odds_movement": "moved from -105 to -110 in last 2 hours",
    }


def fetch_injuries(event_hint: str) -> str:
    # TODO: replace with real ESPN / Sportradar injury report call
    # GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/injuries
    return "No significant injuries reported."


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_sports_agent(market_id: str, event_hint: str = "") -> ResearchOutput:
    try:
        odds = fetch_odds(event_hint)
        injury_notes = fetch_injuries(event_hint)
        data_quality = 0.0  # TODO: set to 1.0 once real API calls are wired in
    except Exception as e:
        return ResearchOutput(
            agent="sports",
            market_id=market_id,
            applicable=False,
            evidence=SportsEvidence(
                event_name=event_hint or market_id,
                odds_snapshot="unavailable",
                raw_text=f"Data fetch failed: {e}",
            ),
            data_quality=0.0,
            sources=[],
        )

    evidence = SportsEvidence(
        event_name=odds["event_name"],
        odds_snapshot=odds["odds_snapshot"],
        odds_movement=odds.get("odds_movement"),
        injury_notes=injury_notes,
        raw_text=(
            f"event={odds['event_name']} "
            f"odds={odds['odds_snapshot']} "
            f"movement={odds.get('odds_movement')} "
            f"injuries={injury_notes}"
        ),
    )

    return ResearchOutput(
        agent="sports",
        market_id=market_id,
        applicable=True,
        evidence=evidence,
        data_quality=data_quality,
        sources=["the-odds-api.com", "espn.com"],
    )


if __name__ == "__main__":
    market_id = sys.argv[1] if len(sys.argv) > 1 else "KXNBA-25DEC25-LAKERS"
    event_hint = sys.argv[2] if len(sys.argv) > 2 else "Lakers vs Celtics"
    print(run_sports_agent(market_id, event_hint).model_dump_json(indent=2))
