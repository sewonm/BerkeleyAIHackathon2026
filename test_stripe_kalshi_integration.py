"""
Test script for Stripe-Kalshi integration

This script demonstrates:
1. Creating a Stripe payment intent
2. Verifying payment
3. Executing a Kalshi trade with verified payment
4. Real money trading flow

Usage:
    python test_stripe_kalshi_integration.py
"""

import os
import sys
import json
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from standalone agent
sys.path.append(os.path.join(os.path.dirname(__file__), "uagents_deploy"))
from standalone_kalshi_agent import (
    StripeAPIClient,
    KalshiAPIClient,
    ExecutionEngine,
    KalshiOrderRequest,
)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_stripe_payment_creation():
    """Test creating a Stripe payment intent"""
    print_section("TEST 1: Create Stripe Payment Intent")

    stripe_client = StripeAPIClient()

    if not stripe_client.api_key:
        print("❌ SKIPPED: No Stripe API key configured")
        print("Set STRIPE_SECRET_KEY in .env file")
        return None

    # Create payment intent for $10.00
    payment = stripe_client.create_payment_intent(
        amount=1000,  # $10.00 in cents
        currency="usd",
        metadata={
            "market_id": "KXPRESI-2024",
            "decision_id": "test-decision",
            "source": "test_script",
        },
    )

    if payment:
        print("✅ Payment intent created successfully!")
        print(f"   Payment ID: {payment['id']}")
        print(f"   Amount: ${payment['amount'] / 100:.2f}")
        print(f"   Status: {payment['status']}")
        print(f"   Client Secret: {payment['client_secret'][:20]}...")
        return payment["id"]
    else:
        print("❌ Failed to create payment intent")
        return None


def test_stripe_payment_verification(payment_intent_id: Optional[str]):
    """Test verifying a Stripe payment intent"""
    print_section("TEST 2: Verify Stripe Payment")

    if not payment_intent_id:
        print("❌ SKIPPED: No payment intent ID provided")
        return False

    stripe_client = StripeAPIClient()

    payment = stripe_client.verify_payment_intent(payment_intent_id)

    if payment:
        print("✅ Payment verified successfully!")
        print(f"   Payment ID: {payment['id']}")
        print(f"   Status: {payment['status']}")
        print(f"   Amount: ${payment['amount'] / 100:.2f}")
        return payment["status"] == "succeeded"
    else:
        print("⚠️  Payment not succeeded yet")
        print(f"   Payment needs to be completed before trade execution")
        print(f"   Status: {payment.get('status') if payment else 'unknown'}")
        return False


def test_kalshi_login():
    """Test logging in to Kalshi"""
    print_section("TEST 3: Kalshi API Login")

    kalshi_client = KalshiAPIClient()

    if not kalshi_client.email or not kalshi_client.password:
        print("❌ SKIPPED: No Kalshi credentials configured")
        print("Set KALSHI_EMAIL and KALSHI_PASSWORD in .env file")
        return False

    success = kalshi_client.login()

    if success:
        print("✅ Logged in to Kalshi successfully!")
        print(f"   User ID: {kalshi_client.user_id}")
        print(f"   Mode: {'DEMO' if kalshi_client.use_demo else 'PRODUCTION'}")

        # Get balance
        balance = kalshi_client.get_balance()
        if balance:
            print(f"   Balance: ${balance.get('balance', 0) / 100:.2f}")

        return True
    else:
        print("❌ Failed to login to Kalshi")
        return False


def test_market_data(market_id: str = "KXPRESI-2024"):
    """Test fetching market data"""
    print_section("TEST 4: Fetch Market Data")

    kalshi_client = KalshiAPIClient()

    if not kalshi_client.login():
        print("❌ SKIPPED: Not logged in to Kalshi")
        return None

    market = kalshi_client.get_market(market_id)

    if market:
        print(f"✅ Market data retrieved successfully!")
        print(f"   Market ID: {market.get('ticker')}")
        print(f"   Title: {market.get('title')}")
        print(f"   YES Bid: {market.get('yes_bid', 'N/A')}¢")
        print(f"   YES Ask: {market.get('yes_ask', 'N/A')}¢")
        print(f"   NO Bid: {market.get('no_bid', 'N/A')}¢")
        print(f"   NO Ask: {market.get('no_ask', 'N/A')}¢")
        print(f"   Volume: {market.get('volume', 'N/A')}")
        return market
    else:
        print(f"❌ Failed to fetch market data for {market_id}")
        return None


def test_trade_execution_without_payment():
    """Test executing a trade without payment verification"""
    print_section("TEST 5: Execute Trade (No Payment Verification)")

    kalshi_client = KalshiAPIClient()
    stripe_client = StripeAPIClient()
    execution_engine = ExecutionEngine(kalshi_client, stripe_client)

    # Create order request
    order_request = KalshiOrderRequest(
        decision_id="test-decision-no-payment",
        market_id="KXPRESI-2024",
        action="BUY_YES",
        quantity=1,  # Buy 1 contract
        order_type="limit",
        limit_price=52,  # 52 cents
        max_slippage=0.02,
        execution_strategy="smart",
        # No payment verification
        require_payment_verification=False,
    )

    print("📋 Order Details:")
    print(f"   Market: {order_request.market_id}")
    print(f"   Action: {order_request.action}")
    print(f"   Quantity: {order_request.quantity}")
    print(f"   Limit Price: {order_request.limit_price}¢")
    print(f"   Payment Verification: {order_request.require_payment_verification}")
    print()

    # Execute order
    order_status = execution_engine.execute_order(order_request)

    if order_status.status != "error":
        print("✅ Order executed successfully!")
        print(f"   Order ID: {order_status.order_id}")
        print(f"   Status: {order_status.status}")
        print(f"   Filled Quantity: {order_status.filled_quantity}")
        if order_status.average_fill_price:
            print(f"   Avg Fill Price: {order_status.average_fill_price:.2%}")
        if order_status.total_cost:
            print(f"   Total Cost: ${order_status.total_cost:.2f}")
    else:
        print("❌ Order execution failed")
        print(f"   Error: {order_status.error_message}")

    return order_status


def test_trade_execution_with_payment(payment_intent_id: Optional[str]):
    """Test executing a trade with payment verification"""
    print_section("TEST 6: Execute Trade (With Payment Verification)")

    if not payment_intent_id:
        print("❌ SKIPPED: No payment intent ID provided")
        return None

    kalshi_client = KalshiAPIClient()
    stripe_client = StripeAPIClient()
    execution_engine = ExecutionEngine(kalshi_client, stripe_client)

    # Create order request with payment verification
    order_request = KalshiOrderRequest(
        decision_id="test-decision-with-payment",
        market_id="KXPRESI-2024",
        action="BUY_YES",
        quantity=10,  # Buy 10 contracts
        order_type="limit",
        limit_price=52,  # 52 cents
        max_slippage=0.02,
        execution_strategy="smart",
        # With payment verification
        payment_intent_id=payment_intent_id,
        require_payment_verification=True,
    )

    print("📋 Order Details:")
    print(f"   Market: {order_request.market_id}")
    print(f"   Action: {order_request.action}")
    print(f"   Quantity: {order_request.quantity}")
    print(f"   Limit Price: {order_request.limit_price}¢")
    print(f"   Payment Intent: {payment_intent_id}")
    print(f"   Payment Verification: {order_request.require_payment_verification}")
    print()

    # Execute order
    order_status = execution_engine.execute_order(order_request)

    if order_status.status != "error":
        print("✅ Order executed successfully!")
        print(f"   Order ID: {order_status.order_id}")
        print(f"   Status: {order_status.status}")
        print(f"   Filled Quantity: {order_status.filled_quantity}")
        if order_status.average_fill_price:
            print(f"   Avg Fill Price: {order_status.average_fill_price:.2%}")
        if order_status.total_cost:
            print(f"   Total Cost: ${order_status.total_cost:.2f}")
    else:
        print("⚠️  Order execution failed (expected if payment not completed)")
        print(f"   Error: {order_status.error_message}")

    return order_status


def test_complete_flow():
    """Test the complete Stripe -> Kalshi trading flow"""
    print_section("COMPLETE INTEGRATION TEST")

    print("This test demonstrates the full payment-to-trade flow:")
    print("1. Create Stripe payment intent")
    print("2. [Manual] User completes payment")
    print("3. Verify payment")
    print("4. Execute Kalshi trade")
    print()

    # Step 1: Create payment intent
    payment_intent_id = test_stripe_payment_creation()

    # Step 2: Verify payment (will fail if not completed)
    if payment_intent_id:
        print()
        print("⚠️  IMPORTANT: Payment needs to be completed manually")
        print(f"   1. Go to Stripe Dashboard")
        print(f"   2. Find payment intent: {payment_intent_id}")
        print(f"   3. Use test card: 4242 4242 4242 4242")
        print(f"   4. Complete the payment")
        print()
        input("Press Enter after completing payment...")

        test_stripe_payment_verification(payment_intent_id)

    # Step 3: Login to Kalshi
    test_kalshi_login()

    # Step 4: Get market data
    test_market_data()

    # Step 5: Execute trade without payment (should work)
    print()
    print("Testing trade execution WITHOUT payment verification...")
    test_trade_execution_without_payment()

    # Step 6: Execute trade with payment (requires completed payment)
    if payment_intent_id:
        print()
        print("Testing trade execution WITH payment verification...")
        test_trade_execution_with_payment(payment_intent_id)


def main():
    """Main test runner"""
    print("\n" + "=" * 80)
    print("  STRIPE-KALSHI INTEGRATION TEST SUITE")
    print("=" * 80)
    print()
    print("This test suite validates the integration between:")
    print("  - Stripe payment processing")
    print("  - Kalshi prediction market trading")
    print("  - ASI One agent communication")
    print()

    # Check environment variables
    print("Configuration Check:")
    print(f"  STRIPE_SECRET_KEY: {'✓' if os.getenv('STRIPE_SECRET_KEY') else '✗ Missing'}")
    print(f"  KALSHI_EMAIL: {'✓' if os.getenv('KALSHI_EMAIL') else '✗ Missing'}")
    print(f"  KALSHI_PASSWORD: {'✓' if os.getenv('KALSHI_PASSWORD') else '✗ Missing'}")
    print(f"  KALSHI_USE_DEMO: {os.getenv('KALSHI_USE_DEMO', 'true')}")
    print()

    # Run tests
    try:
        # Individual tests
        print("\n[Option 1] Run individual tests")
        print("[Option 2] Run complete flow test")
        print()
        choice = input("Select option (1 or 2, or press Enter for complete flow): ").strip()

        if choice == "1":
            # Run individual tests
            payment_id = test_stripe_payment_creation()
            test_stripe_payment_verification(payment_id)
            test_kalshi_login()
            test_market_data()
            test_trade_execution_without_payment()
        else:
            # Run complete flow
            test_complete_flow()

        print_section("TEST SUMMARY")
        print("✅ All tests completed!")
        print()
        print("Next Steps:")
        print("  1. Review test results above")
        print("  2. Configure environment variables if needed")
        print("  3. Complete Stripe payment for paid trade test")
        print("  4. Deploy agent to Agentverse")
        print("  5. Test via DeltaV")
        print()

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
