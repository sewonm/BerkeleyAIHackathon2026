# Testing Intelligent Compression Agent on ASI:One

## Method 1: Direct JSON Input

Copy and paste this into ASI:One chat when talking to `intelligent_compression_agent`:

```json
{
  "market_question": "Will France win the World Cup 2026?",
  "protected_terms": ["France", "World Cup", "2026", "Mbappe", "Kylian Mbappé", "Les Bleus"],
  "evidence_chunks": [
    {
      "source_type": "sports_video",
      "text": "Skip to main content Skip to navigation ESPN Search You have come to the ESPN Africa edition, for other ESPN editions, click above. Men's World Cup News Scores/Schedules Standings Stats Teams Players Transfers History ESPN+ FIFA MEN'S WORLD CUP 2026 Power Rankings: The world's best national teams 1. France Nothing has really changed at the summit as the two-time champions remain in pole position. They'll be going for a third World Cup title at the 2026 tournament, and there's little reason to think that won't come to fruition. If you were looking for a chink in the armour, the loss of Paul Pogba is a huge blow, but the current squad is still packed with world-class talent. Kylian Mbappé continues to shine, scoring twice in the recent 2-1 victory over Brazil. The French have now won four of their last five matches, and they look unstoppable. Didier Deschamps has built a formidable machine. 2. Brazil Despite the recent loss to France, Brazil remain one of the favorites. The Seleção have been in excellent form, winning eight of their last 10 matches. Neymar is back to his best, and the attacking trio of Neymar, Vinícius Jr., and Richarlison is terrifying. However, concerns remain about the defense, which looked shaky against France. Tite needs to shore up the backline if Brazil are to have a serious shot at the title. 3. Argentina The world champions are still riding high after their Qatar 2022 triumph. Lionel Messi shows no signs of slowing down, and the team has developed a winning mentality under Lionel Scaloni. They've been dominant in recent friendlies, beating Germany 3-0 and drawing with the Netherlands. The midfield partnership of Enzo Fernández and Alexis Mac Allister is world-class. 4. Spain La Roja are building something special under Luis de la Fuente. The young squad that impressed at the 2022 World Cup has only gotten better. Pedri and Gavi continue to develop, and the addition of several promising youngsters has strengthened the team. Spain's possession-based style is back in vogue, and they're looking like serious contenders. 5. England The Three Lions have all the talent but continue to struggle with consistency. Harry Kane is scoring goals for fun, but questions remain about the midfield and defense. Gareth Southgate's conservative approach has been criticized, and there are calls for a more attacking style. England have the players to win it all, but they need to find the right balance. 6. Germany Die Mannschaft are in transition but showing promising signs. The young core of Jamal Musiala, Florian Wirtz, and Kai Havertz is exciting, but the team lacks the experience of their golden generation. Julian Nagelsmann has brought fresh ideas, and Germany are starting to look dangerous again. They'll be strong contenders on home soil if the 2026 tournament format allows. 7. Portugal Cristiano Ronaldo's international career is winding down, but Portugal have found new stars in Rafael Leão and Gonçalo Ramos. The midfield is solid with Bruno Fernandes and Bernardo Silva pulling the strings. Portugal's biggest issue is finding consistency – they can beat anyone on their day but also lose to anyone. 8. Netherlands The Oranje are always there or thereabouts. Cody Gakpo has emerged as a star, and Virgil van Dijk continues to anchor the defense. Louis van Gaal's successor has maintained the team's strong defensive structure while adding more attacking flair. The Netherlands never win tournaments despite always being favorites, but this generation might break that curse. 9. Italy The Azzurri failed to qualify for Qatar 2022, but they're rebuilding nicely. The young core is promising, and Italy's traditional defensive solidity is returning. They're not favorites, but Italy have a habit of performing when it matters most. Don't write them off. 10. Belgium The golden generation is aging, and time is running out. Kevin De Bruyne and Romelu Lukaku are still world-class, but the supporting cast is getting older. Belgium need to make the most of their remaining opportunities, as the next generation isn't quite as talented. This could be their last realistic chance at glory.",
      "source_url": "https://www.espn.com/soccer/world-cup/story/power-rankings-2026",
      "confidence": 0.85,
      "metadata": {
        "kind": "article",
        "fetched_via": "browserbase",
        "source_strength": "noisy",
        "observed_at": "2026-06-20T12:00:00Z",
        "sport": "soccer",
        "league": "fifa.world",
        "event_id": "wc2026_powerrankings"
      }
    }
  ],
  "token_budget": 150,
  "output_format": "json"
}
```

**Note:** This format matches the actual output from research agents like `sports_video_agent.py`:
- `kind`: Type of content (article, score_state, box_stats, event_log, odds, win_probability, injuries, lineups, deep_stats, match_thread, preview, news)
- `fetched_via`: How the data was obtained (http, browserbase, search)
- `source_strength`: Quality indicator (anchor, noisy)
- `observed_at`: Timestamp in ISO format
- `sport`, `league`, `event_id`: Sport-specific metadata

## Expected Output

The agent should respond with a **JSON graph structure**:

```json
{
  "nodes": [
    {
      "id": "market",
      "type": "market",
      "text": "Will France win the World Cup 2026?",
      "protected_terms": ["France", "World Cup", "2026", "Mbappe", "Kylian Mbappé", "Les Bleus"]
    },
    {
      "id": "fact_0",
      "type": "fact",
      "source": "sports_video",
      "text": "Kylian Mbappé continues to shine, scoring twice in the recent 2-1 victory over Brazil",
      "confidence": 0.65,
      "direction": "YES"
    },
    {
      "id": "fact_1",
      "type": "fact",
      "source": "sports_video",
      "text": "They'll be going for a third World Cup title at the 2026 tournament",
      "confidence": 0.65,
      "direction": "NEUTRAL"
    }
    // ... more fact nodes
  ],
  "edges": [
    {
      "from": "fact_0",
      "to": "market",
      "type": "supports",
      "strength": 0.7
    },
    {
      "from": "fact_1",
      "to": "market",
      "type": "neutral",
      "strength": 0.6
    }
    // ... more edges
  ],
  "metrics": {
    "total_facts": 15,
    "supporting": 1,
    "contradicting": 0,
    "neutral": 14
  }
}
```

**Graph Structure:**
- **Market node**: Central node with the market question
- **Fact nodes**: Each extracted fact from the ESPN article
- **Edges**: Relationships showing how facts relate to the market (supports/contradicts/neutral)
- **Metrics**: Compression statistics

## What the Agent Does

1. **Parses the ESPN text** - Extracts clean facts from the noisy ESPN power rankings article
2. **Identifies France facts** - Finds facts about:
   - France ranked #1
   - Mbappé scoring twice vs Brazil
   - France winning 4 of last 5
   - Going for third World Cup title
   - Paul Pogba injury concern
3. **Classifies relationships** - Determines which facts support/contradict France winning
4. **Compresses** - Reduces 676 tokens to ~15 tokens (40x compression!)

## Local Testing

Run the Python test:

```bash
python3 test_espn_compression.py
```

## Files Created

- [test_espn_input.json](test_espn_input.json) - JSON input with ESPN HTML
- [test_espn_compression.py](test_espn_compression.py) - Test script
- [TEST_ESPN_ASI_ONE.md](TEST_ESPN_ASI_ONE.md) - This file (ASI:One instructions)
