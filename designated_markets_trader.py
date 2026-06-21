"""
Designated Markets Trader - Automatically trade on specific Kalshi markets with Stripe payments

This script:
1. Monitors designated markets
2. Gets trading decisions from Decision Agent
3. Processes Stripe payments
4. Executes real trades on Kalshi

Usage:
    python designated_markets_trader.py
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from standalone agents
sys.path.append(os.path.join(os.path.dirname(__file__), "uagents_deploy"))
from standalone_kalshi_agent import (
    StripeAPIClient,
    KalshiAPIClient,
    ExecutionEngine,
    KalshiOrderRequest,
)


# ============================================================================
# DESIGNATED MARKETS CONFIGURATION
# ============================================================================

DESIGNATED_MARKETS = [
    {
        "market_id": "KXPRESI-2024",
        "name": "US Presidential Election 2024",
        "max_investment": 100.00,  # Max $ per trade
        "min_confidence": 0.70,  # Minimum confidence to trade
        "check_interval": 300,  # Check every 5 minutes
    },
    {
        "market_id": "INXM-24DEC31",
        "name": "S&P 500 End of Year",
        "max_investment": 50.00,
        "min_confidence": 0.75,
        "check_interval": 600,  # Check every 10 minutes
    },
    {
        "market_id": "HIGHNY-24",
        "name": "NYC High Temperature",
        "max_investment": 25.00,
        "min_confidence": 0.65,
        "check_interval": 1800,  # Check every 30 minutes
    },
]


# ============================================================================
# TRADING DECISION ENGINE
# ============================================================================

class SimpleDecisionEngine:
    """
    Simplified decision engine for automated trading

    In production, this would integrate with the standalone_decision_agent
    """

    def __init__(self):
        self.decisions_made = 0

    def make_decision(
        self, market: Dict[str, Any], market_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Make a trading decision for a market

        Args:
            market: Market data from Kalshi
            market_config: Configuration for this market

        Returns:
            Trading decision or None if no action
        """
        # Get current prices
        yes_bid = market.get("yes_bid", 50)
        yes_ask = market.get("yes_ask", 50)
        no_bid = market.get("no_bid", 50)
        no_ask = market.get("no_ask", 50)

        # Simple logic: Look for pricing inefficiencies
        # In production, use the Decision Agent with Claude reasoning

        # Check if YES is underpriced (ask < 40 = potential value)
        if yes_ask < 40:
            confidence = 0.65 + ((40 - yes_ask) / 100)  # Higher confidence for lower prices
            if confidence >= market_config["min_confidence"]:
                # Calculate position size
                max_cost = market_config["max_investment"]
                quantity = int(max_cost / (yes_ask / 100))
                quantity = max(1, min(quantity, 100))  # Between 1-100 contracts

                return {
                    "action": "BUY_YES",
                    "quantity": quantity,
                    "limit_price": yes_ask + 2,  # Slight buffer
                    "confidence": confidence,
                    "reasoning": f"YES appears underpriced at {yes_ask}¢",
                }

        # Check if NO is underpriced
        if no_ask < 40:
            confidence = 0.65 + ((40 - no_ask) / 100)
            if confidence >= market_config["min_confidence"]:
                max_cost = market_config["max_investment"]
                quantity = int(max_cost / (no_ask / 100))
                quantity = max(1, min(quantity, 100))

                return {
                    "action": "BUY_NO",
                    "quantity": quantity,
                    "limit_price": no_ask + 2,
                    "confidence": confidence,
                    "reasoning": f"NO appears underpriced at {no_ask}¢",
                }

        # No trading opportunity
        return None


# ============================================================================
# AUTOMATED TRADING SYSTEM
# ============================================================================

class DesignatedMarketsTrader:
    """Automated trading system for designated markets"""

    def __init__(self):
        self.kalshi_client = KalshiAPIClient()
        self.stripe_client = StripeAPIClient()
        self.execution_engine = ExecutionEngine(self.kalshi_client, self.stripe_client)
        self.decision_engine = SimpleDecisionEngine()

        self.trades_executed = 0
        self.total_invested = 0.0
        self.last_check = {}

        # Login to Kalshi
        if not self.kalshi_client.login():
            raise RuntimeError("Failed to login to Kalshi")

        print("✅ Logged in to Kalshi")
        print(f"   Mode: {'DEMO' if self.kalshi_client.use_demo else 'PRODUCTION'}")

        # Check Stripe
        if self.stripe_client.api_key:
            print("✅ Stripe integration enabled")
        else:
            print("⚠️  Stripe integration disabled (no API key)")

    def process_payment(self, amount: float, market_id: str) -> Optional[str]:
        """
        Process Stripe payment for trade

        Args:
            amount: Amount in dollars
            market_id: Market ID for metadata

        Returns:
            Payment intent ID or None
        """
        if not self.stripe_client.api_key:
            print("⚠️  No Stripe API key - skipping payment")
            return None

        # Create payment intent
        payment = self.stripe_client.create_payment_intent(
            amount=int(amount * 100),  # Convert to cents
            metadata={
                "market_id": market_id,
                "source": "designated_markets_trader",
                "timestamp": datetime.now().isoformat(),
            },
        )

        if payment:
            return payment["id"]
        else:
            print("❌ Failed to create payment intent")
            return None

    def check_market(self, market_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check a market for trading opportunities

        Args:
            market_config: Market configuration

        Returns:
            Trade result or None
        """
        market_id = market_config["market_id"]

        # Rate limiting - check if enough time has passed
        last_check = self.last_check.get(market_id, 0)
        if time.time() - last_check < market_config["check_interval"]:
            return None

        self.last_check[market_id] = time.time()

        print(f"\n📊 Checking market: {market_config['name']}")

        # Get market data
        market = self.kalshi_client.get_market(market_id)
        if not market:
            print(f"❌ Failed to fetch market data")
            return None

        print(f"   YES: {market.get('yes_bid', 'N/A')}¢ / {market.get('yes_ask', 'N/A')}¢")
        print(f"   NO:  {market.get('no_bid', 'N/A')}¢ / {market.get('no_ask', 'N/A')}¢")

        # Make decision
        decision = self.decision_engine.make_decision(market, market_config)
        if not decision:
            print(f"   ⏸  No trading opportunity")
            return None

        print(f"   📈 Trading opportunity found!")
        print(f"      Action: {decision['action']}")
        print(f"      Quantity: {decision['quantity']}")
        print(f"      Price: {decision['limit_price']}¢")
        print(f"      Confidence: {decision['confidence']:.1%}")
        print(f"      Reasoning: {decision['reasoning']}")

        # Calculate cost
        estimated_cost = decision["quantity"] * decision["limit_price"] / 100
        print(f"      Est. Cost: ${estimated_cost:.2f}")

        # Process payment if Stripe enabled
        payment_intent_id = None
        if self.stripe_client.api_key:
            print(f"   💳 Processing payment...")
            payment_intent_id = self.process_payment(estimated_cost, market_id)
            if not payment_intent_id:
                print(f"   ❌ Payment failed - aborting trade")
                return None

        # Execute trade
        print(f"   🔄 Executing trade...")

        order_request = KalshiOrderRequest(
            decision_id=f"auto-{market_id}-{int(time.time())}",
            market_id=market_id,
            action=decision["action"],
            quantity=decision["quantity"],
            order_type="limit",
            limit_price=decision["limit_price"],
            max_slippage=0.02,
            execution_strategy="smart",
            payment_intent_id=payment_intent_id,
            require_payment_verification=(payment_intent_id is not None),
        )

        order_status = self.execution_engine.execute_order(order_request)

        if order_status.status != "error":
            self.trades_executed += 1
            self.total_invested += estimated_cost

            print(f"   ✅ Trade executed successfully!")
            print(f"      Order ID: {order_status.order_id}")
            print(f"      Status: {order_status.status}")

            return {
                "market_id": market_id,
                "order_id": order_status.order_id,
                "status": order_status.status,
                "cost": estimated_cost,
                "payment_intent_id": payment_intent_id,
            }
        else:
            print(f"   ❌ Trade execution failed")
            print(f"      Error: {order_status.error_message}")
            return None

    def run(self, duration_seconds: Optional[int] = None):
        """
        Run the automated trading system

        Args:
            duration_seconds: How long to run (None = forever)
        """
        print("\n" + "=" * 80)
        print("  DESIGNATED MARKETS TRADER - STARTING")
        print("=" * 80)
        print()
        print(f"Monitoring {len(DESIGNATED_MARKETS)} markets:")
        for market in DESIGNATED_MARKETS:
            print(f"  - {market['name']} ({market['market_id']})")
        print()
        print("Press Ctrl+C to stop")
        print()

        start_time = time.time()

        try:
            while True:
                # Check if we should stop
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break

                # Check each market
                for market_config in DESIGNATED_MARKETS:
                    try:
                        self.check_market(market_config)
                    except Exception as e:
                        print(f"❌ Error checking {market_config['market_id']}: {e}")

                # Wait before next iteration
                time.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            print("\n\nStopping...")

        # Print summary
        print("\n" + "=" * 80)
        print("  TRADING SUMMARY")
        print("=" * 80)
        print()
        print(f"Trades Executed: {self.trades_executed}")
        print(f"Total Invested: ${self.total_invested:.2f}")
        print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("  DESIGNATED MARKETS TRADER")
    print("=" * 80)
    print()
    print("This system automatically trades on designated Kalshi markets with Stripe payments.")
    print()

    # Check configuration
    print("Configuration:")
    print(f"  KALSHI_EMAIL: {'✓' if os.getenv('KALSHI_EMAIL') else '✗ Missing'}")
    print(f"  KALSHI_PASSWORD: {'✓' if os.getenv('KALSHI_PASSWORD') else '✗ Missing'}")
    print(f"  KALSHI_USE_DEMO: {os.getenv('KALSHI_USE_DEMO', 'true')}")
    print(f"  STRIPE_SECRET_KEY: {'✓' if os.getenv('STRIPE_SECRET_KEY') else '✗ Missing (optional)'}")
    print()

    if not os.getenv("KALSHI_EMAIL") or not os.getenv("KALSHI_PASSWORD"):
        print("❌ Missing required Kalshi credentials")
        print("   Set KALSHI_EMAIL and KALSHI_PASSWORD in .env file")
        return

    # Warning for production mode
    if os.getenv("KALSHI_USE_DEMO", "true").lower() != "true":
        print("⚠️  WARNING: Running in PRODUCTION mode with REAL MONEY")
        print()
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Aborted.")
            return

    # Create and run trader
    try:
        trader = DesignatedMarketsTrader()

        # Ask for duration
        print()
        duration_input = input("How long to run? (minutes, or press Enter for continuous): ").strip()

        if duration_input:
            duration_minutes = int(duration_input)
            duration_seconds = duration_minutes * 60
            print(f"\nRunning for {duration_minutes} minutes...")
        else:
            duration_seconds = None
            print("\nRunning continuously...")

        trader.run(duration_seconds)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
