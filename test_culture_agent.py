"""
Direct test of Browserbase search + fetch used by culture_web_agent.
No uAgents/blockchain needed — just verifies web search and page fetch work.

Usage:
    python test_culture_agent.py ["market question"]

Example:
    python test_culture_agent.py "Will the S&P 500 close above 6000 by end of 2025?"
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Pull in the functions directly from the agent file
sys.path.insert(0, os.path.dirname(__file__))

from uagents_deploy.culture_web_agent import (
    collect_culture_evidence,
    BROWSERBASE_API_KEY,
    SERPER_API_KEY,
)


async def test(market_question: str):
    print(f"\nBrowserbase: {'LIVE' if BROWSERBASE_API_KEY else 'MOCK'}")
    print(f"Serper:      {'LIVE' if SERPER_API_KEY else 'MOCK (BB google fallback)'}")
    print(f"\nQuestion: {market_question}\n")
    print("=" * 60)

    chunks = await collect_culture_evidence(market_question, protected_terms=[])

    print(f"\nGot {len(chunks)} evidence chunks\n")

    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(f"URL:        {chunk.source_url}")
        print(f"Confidence: {chunk.confidence}")
        print(f"Mock:       {chunk.metadata.get('mock')}")
        print(f"Query:      {chunk.metadata.get('query')}")
        print()
        print(chunk.text[:800])
        print()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Will the S&P 500 close above 6000 by end of 2025?"
    asyncio.run(test(question))
