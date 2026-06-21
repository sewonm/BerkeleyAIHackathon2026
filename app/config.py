"""Configuration for the prediction market system"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    EXAMPLES_DIR = PROJECT_ROOT / "examples"
    MARKETS_DIR = EXAMPLES_DIR / "markets"
    RAW_CONTEXT_DIR = EXAMPLES_DIR / "raw_context"
    OUTPUTS_DIR = EXAMPLES_DIR / "outputs"

    # Compression settings
    DEFAULT_TOKEN_BUDGET = 3000
    DEDUPLICATION_THRESHOLD = 0.85

    # MVP mode
    MVP_MODE = True  # Only CultureWebAgent is active
    REQUIRE_API_KEYS = False  # No API keys needed for MVP

    # Future service settings (not used in MVP)
    BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
    KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")
    FETCH_API_KEY = os.getenv("FETCH_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Trading settings (not used in MVP)
    TRADE_MODE = os.getenv("TRADE_MODE", "dry_run")  # dry_run, demo, live
    ENABLE_LIVE_TRADING = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"

    @classmethod
    def get_market_file(cls, filename: str = "culture_market.json") -> Path:
        """Get path to a market file"""
        return cls.MARKETS_DIR / filename

    @classmethod
    def get_output_file(cls, filename: str) -> Path:
        """Get path to an output file"""
        return cls.OUTPUTS_DIR / filename
