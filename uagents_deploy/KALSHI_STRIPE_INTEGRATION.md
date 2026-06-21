# Kalshi Trading Agent - Stripe Integration Guide

Complete guide for using the Kalshi Trading Agent with integrated Stripe payment processing for ASI One.

---

## Overview

The Kalshi Trading Agent now supports **real money trading** with integrated Stripe payment processing. This enables:

- ✅ **Payment verification** before trade execution
- ✅ **ASI One compatible** payment processing
- ✅ **Real trades** with user funds via Stripe
- ✅ **Secure payments** with webhook verification
- ✅ **Automatic fund validation** before placing orders

---

## Features

### 1. **Stripe Payment Integration**
- Create payment intents for trade funding
- Verify payment completion before execution
- Support for Stripe Checkout sessions
- Webhook signature verification for security

### 2. **Real Money Kalshi Trading**
- Execute trades on Kalshi with verified payments
- Support for both demo and production modes
- Real-time market data and order execution
- Smart order routing with slippage protection

### 3. **ASI One Compatibility**
- Designed for ASI One ecosystem
- Chat protocol for DeltaV integration
- Metadata tagging for payment tracking
- Agent-to-agent communication support

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
# Install required packages
pip install requests pydantic uagents

# Optional: Install chat protocol for ASI One
pip install uagents[chat]
```

### Step 2: Create Stripe Account

1. **Go to Stripe**: https://stripe.com
2. **Sign up** for a Stripe account
3. **Get API keys** from Dashboard → Developers → API keys
4. **Get webhook secret** from Dashboard → Developers → Webhooks

### Step 3: Create Kalshi Account

1. **Go to Kalshi**: https://kalshi.com
2. **Sign up** for an account
3. **Use demo mode** for testing (recommended)
4. **Save credentials** (email and password)

### Step 4: Configure Environment Variables

Create a `.env` file with the following:

```bash
# Kalshi credentials
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Use demo for testing

# Stripe API keys
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_ASI_ONE_MODE=true  # Enable ASI One features
```

---

## Usage Examples

### Example 1: Direct Trade (without payment verification)

For agents or automated systems with pre-funded Kalshi accounts:

```json
{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52,
  "execution_strategy": "smart"
}
```

### Example 2: Paid Trade (with Stripe payment)

For users paying via Stripe before trade execution:

**Step 1: Create Payment Intent (Stripe)**

```python
import stripe
stripe.api_key = "sk_test_your_stripe_secret_key"

# Create payment intent
payment_intent = stripe.PaymentIntent.create(
    amount=1000,  # $10.00 in cents
    currency="usd",
    metadata={
        "market_id": "KXPRESI-2024",
        "source": "asi_one",
        "service": "kalshi_trading"
    }
)

print(f"Payment Intent ID: {payment_intent.id}")
```

**Step 2: Send Trade Request with Payment**

```json
{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52,
  "payment_intent_id": "pi_1234567890",
  "require_payment_verification": true
}
```

The agent will:
1. Verify payment with Stripe
2. Check sufficient funds
3. Execute trade on Kalshi
4. Report results

---

## Payment Flow

### Standard Payment Flow

```
1. User initiates payment
   ↓
2. Stripe creates PaymentIntent
   ↓
3. User completes payment (card, etc.)
   ↓
4. Agent receives payment_intent_id
   ↓
5. Agent verifies payment succeeded
   ↓
6. Agent checks payment amount ≥ trade cost
   ↓
7. Agent executes trade on Kalshi
   ↓
8. Agent reports execution results
```

### ASI One Payment Flow

```
1. User requests trade via DeltaV
   ↓
2. Agent creates Stripe Checkout session
   ↓
3. User redirected to Stripe Checkout
   ↓
4. User completes payment
   ↓
5. Stripe webhook notifies agent
   ↓
6. Agent executes trade automatically
   ↓
7. Agent sends results to user
```

---

## API Reference

### Stripe Client Methods

#### `create_payment_intent(amount, currency, customer_id, metadata)`

Create a payment intent for funding trades.

**Parameters:**
- `amount` (int): Amount in cents (e.g., 1000 = $10.00)
- `currency` (str): Currency code (default: "usd")
- `customer_id` (str, optional): Stripe customer ID
- `metadata` (dict, optional): Additional metadata

**Returns:** Payment intent data or None

#### `verify_payment_intent(payment_intent_id)`

Verify a payment intent is successful.

**Parameters:**
- `payment_intent_id` (str): Payment intent ID

**Returns:** Payment intent data or None if not successful

#### `create_checkout_session(amount, market_id, success_url, cancel_url, metadata)`

Create a Stripe Checkout session for ASI One users.

**Parameters:**
- `amount` (int): Amount in cents
- `market_id` (str): Kalshi market ID
- `success_url` (str): URL to redirect on success
- `cancel_url` (str): URL to redirect on cancel
- `metadata` (dict, optional): Additional metadata

**Returns:** Checkout session data or None

---

## Order Request Schema

```python
class KalshiOrderRequest(BaseModel):
    request_id: str  # Auto-generated
    decision_id: str  # Reference to trading decision
    market_id: str  # Kalshi ticker (e.g., "KXPRESI-2024")

    # Order details
    action: Literal["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO"]
    quantity: int  # Number of contracts
    order_type: Literal["market", "limit"]  # Default: "limit"
    limit_price: Optional[int]  # Price in cents (0-100)

    # Risk management
    max_slippage: Optional[float]  # Default: 0.02 (2%)
    timeout_seconds: Optional[int]  # Default: 30

    # Execution strategy
    execution_strategy: Optional[Literal["immediate", "passive", "smart"]]  # Default: "smart"

    # Stripe payment integration (optional)
    payment_intent_id: Optional[str]  # Link to Stripe payment
    require_payment_verification: bool  # Default: False
```

---

## Order Response Schema

```python
class KalshiOrderStatus(BaseModel):
    order_id: str
    request_id: str
    market_id: str

    status: Literal[
        "pending",
        "submitted",
        "partially_filled",
        "filled",
        "cancelled",
        "rejected",
        "error"
    ]

    # Fill details
    filled_quantity: int
    average_fill_price: Optional[float]
    total_cost: Optional[float]

    # Timestamps
    submitted_at: Optional[datetime]
    filled_at: Optional[datetime]
    updated_at: datetime

    # Error details
    error_message: Optional[str]
    rejection_reason: Optional[str]
```

---

## Security Best Practices

### 1. **API Key Management**
- ✅ Use environment variables for API keys
- ✅ Never commit API keys to version control
- ✅ Use test keys for development
- ✅ Rotate production keys regularly

### 2. **Payment Verification**
- ✅ Always verify payment_intent status
- ✅ Check payment amount before execution
- ✅ Use webhook signatures for authenticity
- ✅ Log all payment verifications

### 3. **Order Execution**
- ✅ Use demo mode for testing
- ✅ Implement slippage limits
- ✅ Set position size limits
- ✅ Monitor execution logs

### 4. **ASI One Integration**
- ✅ Tag all payments with metadata
- ✅ Track payment_intent_id for reconciliation
- ✅ Implement timeout handling
- ✅ Provide clear error messages

---

## Testing

### Local Testing

```bash
# Run the agent locally
cd uagents_deploy
python standalone_kalshi_agent.py
```

**Expected Output:**
```
[kalshi_execution_agent] Kalshi Execution Agent started!
Address: agent1q...
Mode: DEMO
Ready to execute orders on Kalshi
Custom protocol: ENABLED (agent-to-agent communication)
ASI:One chat protocol: ENABLED (DeltaV compatible)
Stripe integration: ENABLED (ASI One payment processing)
ASI One Mode: ENABLED
Logged in to Kalshi successfully
Account balance: $10000.00
```

### Test Payment Verification

```python
from standalone_kalshi_agent import StripeAPIClient

stripe_client = StripeAPIClient()

# Create test payment intent
payment = stripe_client.create_payment_intent(
    amount=1000,  # $10.00
    metadata={
        "market_id": "TEST-MARKET",
        "test_mode": "true"
    }
)

print(f"Payment Intent: {payment['id']}")

# Verify payment
verified = stripe_client.verify_payment_intent(payment['id'])
print(f"Verified: {verified is not None}")
```

### Test Trade Execution

```python
from standalone_kalshi_agent import KalshiOrderRequest, ExecutionEngine

request = KalshiOrderRequest(
    decision_id="test-decision",
    market_id="KXPRESI-2024",
    action="BUY_YES",
    quantity=10,
    order_type="limit",
    limit_price=52,
    payment_intent_id="pi_1234567890",
    require_payment_verification=True
)

status = execution_engine.execute_order(request)
print(f"Order Status: {status.status}")
print(f"Order ID: {status.order_id}")
```

---

## Deployment to Agentverse

### Step 1: Deploy Agent

1. Go to **Agentverse**: https://agentverse.ai/
2. Create new agent
3. Select **"Agent Chat Protocol (ASI) - Discoverable"**
4. Upload `standalone_kalshi_agent.py`

### Step 2: Set Environment Variables

In Agentverse UI, set:
```
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_ASI_ONE_MODE=true
```

### Step 3: Deploy and Test

1. Click **"Deploy"**
2. Wait for green status
3. Copy agent address
4. Test on DeltaV

---

## Troubleshooting

### Issue: "Payment verification failed"

**Cause:** Payment not completed or invalid payment_intent_id

**Fix:**
1. Check payment_intent status on Stripe Dashboard
2. Ensure payment is marked as "succeeded"
3. Verify correct payment_intent_id in request

### Issue: "Insufficient payment"

**Cause:** Payment amount less than estimated trade cost

**Fix:**
1. Calculate trade cost: `quantity * limit_price / 100`
2. Create payment intent with sufficient amount
3. Include buffer for slippage and fees

### Issue: "Failed to login to Kalshi"

**Cause:** Invalid Kalshi credentials

**Fix:**
1. Verify `KALSHI_EMAIL` and `KALSHI_PASSWORD`
2. Check if account is active
3. Try logging in manually at kalshi.com

### Issue: "Stripe integration: DISABLED"

**Cause:** Missing `STRIPE_SECRET_KEY`

**Fix:**
1. Set `STRIPE_SECRET_KEY` in environment
2. Restart agent
3. Check logs for "Stripe integration: ENABLED"

---

## Example: Complete Trading Flow

### Step 1: User Requests Trade via DeltaV

User: *"I want to buy 10 YES contracts on KXPRESI-2024 at 52 cents"*

### Step 2: Agent Creates Payment Request

```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
  "amount": "$5.20",
  "market": "KXPRESI-2024",
  "contracts": 10
}
```

### Step 3: User Completes Payment

User clicks checkout URL and pays $5.20

### Step 4: Agent Verifies Payment

```
[StripeClient] Payment verified: pi_1234567890 ($5.20)
```

### Step 5: Agent Executes Trade

```
[KalshiClient] Placing order: BUY_YES 10 contracts @ 52¢
[KalshiClient] Order placed successfully: order_abc123
```

### Step 6: Agent Reports Results

```json
{
  "order_id": "order_abc123",
  "status": "filled",
  "filled_quantity": 10,
  "average_fill_price": 0.52,
  "total_cost": 5.20,
  "payment_verified": true
}
```

---

## Advanced Features

### Custom Execution Strategies

**Immediate:** Execute at market price immediately
```json
{
  "execution_strategy": "immediate",
  "order_type": "market"
}
```

**Passive:** Post limit order and wait for fill
```json
{
  "execution_strategy": "passive",
  "order_type": "limit",
  "limit_price": 52
}
```

**Smart:** Automatically determine best execution
```json
{
  "execution_strategy": "smart",
  "max_slippage": 0.02
}
```

### Slippage Protection

```json
{
  "action": "BUY_YES",
  "quantity": 10,
  "limit_price": 52,
  "max_slippage": 0.01  // 1% max slippage
}
```

Agent will reject if market moves more than 1% from limit_price.

---

## Resources

- **Kalshi API Docs**: https://trading-api.readme.io/reference/getting-started
- **Stripe API Docs**: https://stripe.com/docs/api
- **ASI One Docs**: https://uagents.fetch.ai/docs/examples/asi-1
- **Agentverse**: https://agentverse.ai/
- **DeltaV**: https://deltav.agentverse.ai/

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review agent logs for error messages
3. Test in demo mode first
4. Verify all environment variables
5. Contact support with detailed error logs

---

## Summary

The Kalshi Trading Agent with Stripe integration provides:

✅ **Real money trading** via Stripe payment processing
✅ **ASI One compatibility** for DeltaV integration
✅ **Payment verification** before trade execution
✅ **Secure webhooks** for payment confirmation
✅ **Smart execution** with slippage protection
✅ **Demo mode** for safe testing

Ready to deploy on Agentverse and use with real money!
