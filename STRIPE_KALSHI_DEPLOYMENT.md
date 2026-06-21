# Stripe-Kalshi Integration Deployment Guide

Complete guide for deploying the Kalshi Trading Agent with Stripe payment integration to ASI One.

---

## 🎯 What's New

The standalone_kalshi_agent.py now includes:

✅ **Stripe Payment Integration** - Process real payments before trades
✅ **Payment Verification** - Verify payment completion before execution
✅ **ASI One Compatibility** - Works with DeltaV and ASI ecosystem
✅ **Real Money Trading** - Execute trades on Kalshi with user funds
✅ **Designated Markets** - Automated trading on specific markets
✅ **Secure Webhooks** - Verify Stripe webhook signatures

---

## 📋 Changes Made

### 1. Enhanced `standalone_kalshi_agent.py`

**New Features:**
- `StripeAPIClient` class for payment processing
- Payment verification before trade execution
- Support for `payment_intent_id` in order requests
- ASI One metadata tagging
- Stripe Checkout session creation
- Webhook signature verification

**New Environment Variables:**
- `STRIPE_SECRET_KEY` - Stripe API secret key
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key
- `STRIPE_WEBHOOK_SECRET` - Webhook signing secret
- `STRIPE_ASI_ONE_MODE` - Enable ASI One features

### 2. New Files Created

**Documentation:**
- `KALSHI_STRIPE_INTEGRATION.md` - Complete integration guide
- `STRIPE_KALSHI_DEPLOYMENT.md` - This deployment guide

**Testing:**
- `test_stripe_kalshi_integration.py` - Integration test suite
- `designated_markets_trader.py` - Automated trading system

### 3. Updated Files

**Configuration:**
- `.env.example` - Added Stripe configuration
- Updated with Kalshi email/password format

---

## 🚀 Quick Start

### Option 1: Test Locally

```bash
# 1. Install dependencies
pip install requests pydantic uagents python-dotenv

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Run integration tests
python test_stripe_kalshi_integration.py

# 4. Run designated markets trader
python designated_markets_trader.py
```

### Option 2: Deploy to Agentverse

```bash
# 1. Go to Agentverse
https://agentverse.ai/

# 2. Create new agent
- Select "Agent Chat Protocol (ASI) - Discoverable"

# 3. Upload agent
- Upload: uagents_deploy/standalone_kalshi_agent.py

# 4. Set environment variables
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_ASI_ONE_MODE=true

# 5. Deploy and test on DeltaV
```

---

## 🔐 Security Setup

### Stripe Setup

1. **Create Stripe Account**
   - Go to https://stripe.com
   - Sign up for account
   - Activate test mode

2. **Get API Keys**
   - Dashboard → Developers → API keys
   - Copy "Secret key" (starts with `sk_test_`)
   - Copy "Publishable key" (starts with `pk_test_`)

3. **Setup Webhooks**
   - Dashboard → Developers → Webhooks
   - Add endpoint: `https://your-agent.agentverse.ai/webhook`
   - Select events: `payment_intent.succeeded`
   - Copy webhook signing secret (starts with `whsec_`)

### Kalshi Setup

1. **Create Kalshi Account**
   - Go to https://kalshi.com
   - Sign up for account
   - Use demo mode for testing

2. **Get Credentials**
   - Email: Your login email
   - Password: Your account password
   - Demo mode: Set `KALSHI_USE_DEMO=true`

---

## 📝 Environment Configuration

Create `.env` file:

```bash
# Kalshi API
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Use demo for testing

# Stripe API
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_ASI_ONE_MODE=true

# Optional: Agent configuration
AGENT_NAME=kalshi_execution_agent
AGENT_SEED=your_unique_seed
AGENT_PORT=8004
```

---

## 🧪 Testing Guide

### Test 1: Stripe Payment Creation

```bash
python test_stripe_kalshi_integration.py
```

**Expected Output:**
```
✅ Payment intent created successfully!
   Payment ID: pi_1234567890
   Amount: $10.00
   Status: requires_payment_method
```

### Test 2: Kalshi Connection

**Expected Output:**
```
✅ Logged in to Kalshi successfully!
   User ID: user_abc123
   Mode: DEMO
   Balance: $10000.00
```

### Test 3: Market Data

**Expected Output:**
```
✅ Market data retrieved successfully!
   Market ID: KXPRESI-2024
   YES Bid: 48¢
   YES Ask: 52¢
   NO Bid: 48¢
   NO Ask: 52¢
```

### Test 4: Trade Execution

**Expected Output:**
```
✅ Order executed successfully!
   Order ID: order_abc123
   Status: filled
   Filled Quantity: 10
   Avg Fill Price: 52.0%
   Total Cost: $5.20
```

---

## 🎮 Usage Examples

### Example 1: Simple Trade (No Payment)

```json
{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52
}
```

### Example 2: Paid Trade (With Stripe)

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

### Example 3: Automated Trading

```bash
# Run designated markets trader
python designated_markets_trader.py

# Enter duration (or press Enter for continuous)
How long to run? (minutes, or press Enter for continuous): 60

# Monitor automated trades
📊 Checking market: US Presidential Election 2024
   YES: 48¢ / 52¢
   NO:  48¢ / 52¢
   📈 Trading opportunity found!
      Action: BUY_YES
      Quantity: 10
      Price: 54¢
      Confidence: 75.0%
   💳 Processing payment...
   🔄 Executing trade...
   ✅ Trade executed successfully!
```

---

## 🌐 ASI One Integration

### DeltaV Usage

1. **Search for agent** on DeltaV
   - Search: "Kalshi Trading Agent"
   - Or use agent address directly

2. **Send request**
   ```
   I want to buy 10 YES contracts on KXPRESI-2024 at 52 cents
   ```

3. **Agent responds with payment link**
   ```
   Payment required: $5.20
   Click here to pay: https://checkout.stripe.com/pay/cs_test_...
   ```

4. **Complete payment**
   - Click payment link
   - Enter test card: 4242 4242 4242 4242
   - Complete checkout

5. **Trade executes automatically**
   ```
   ✅ Payment verified: $5.20
   ✅ Order executed: order_abc123
   Status: filled
   Fill Price: 52¢
   Total Cost: $5.20
   ```

### Agent-to-Agent Communication

```python
from uagents import Agent, Context

orchestrator = Agent(name="orchestrator", seed="orch123", port=8001)

KALSHI_AGENT = "agent1q..."  # Your deployed agent address

@orchestrator.on_event("startup")
async def send_trade_request(ctx: Context):
    # Create payment intent
    payment = stripe.PaymentIntent.create(amount=520)

    # Send trade request
    request = KalshiOrderRequest(
        decision_id="orch-decision-1",
        market_id="KXPRESI-2024",
        action="BUY_YES",
        quantity=10,
        order_type="limit",
        limit_price=52,
        payment_intent_id=payment.id,
        require_payment_verification=True
    )

    await ctx.send(KALSHI_AGENT, request)
```

---

## 🐛 Troubleshooting

### Issue: "Stripe integration: DISABLED"

**Fix:**
```bash
# Set Stripe API key
export STRIPE_SECRET_KEY=sk_test_your_key

# Or in .env file
echo "STRIPE_SECRET_KEY=sk_test_your_key" >> .env
```

### Issue: "Payment verification failed"

**Fix:**
1. Check payment intent status on Stripe Dashboard
2. Ensure payment is marked as "succeeded"
3. Use test card: 4242 4242 4242 4242
4. Complete 3D Secure if required

### Issue: "Insufficient payment"

**Fix:**
```python
# Calculate required amount
cost = quantity * limit_price / 100
buffer = cost * 0.05  # 5% buffer
total = cost + buffer

# Create payment with buffer
payment = stripe.PaymentIntent.create(
    amount=int(total * 100)  # Convert to cents
)
```

### Issue: "Failed to login to Kalshi"

**Fix:**
```bash
# Verify credentials
echo $KALSHI_EMAIL
echo $KALSHI_PASSWORD

# Test login manually
curl -X POST https://demo-api.kalshi.co/trade-api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your_email","password":"your_password"}'
```

---

## 📊 Designated Markets

The system supports automated trading on specific markets:

### Configured Markets

1. **US Presidential Election 2024** (`KXPRESI-2024`)
   - Max investment: $100/trade
   - Min confidence: 70%
   - Check interval: 5 minutes

2. **S&P 500 End of Year** (`INXM-24DEC31`)
   - Max investment: $50/trade
   - Min confidence: 75%
   - Check interval: 10 minutes

3. **NYC High Temperature** (`HIGHNY-24`)
   - Max investment: $25/trade
   - Min confidence: 65%
   - Check interval: 30 minutes

### Add Custom Markets

Edit `designated_markets_trader.py`:

```python
DESIGNATED_MARKETS = [
    {
        "market_id": "YOUR-MARKET-ID",
        "name": "Your Market Name",
        "max_investment": 100.00,
        "min_confidence": 0.70,
        "check_interval": 300,
    },
]
```

---

## 🔄 Payment Flow Diagram

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ Request trade
       ▼
┌─────────────┐
│ Kalshi Agent│
└──────┬──────┘
       │ Create payment intent
       ▼
┌─────────────┐
│   Stripe    │
└──────┬──────┘
       │ Payment URL
       ▼
┌─────────────┐
│    User     │
└──────┬──────┘
       │ Complete payment
       ▼
┌─────────────┐
│   Stripe    │
└──────┬──────┘
       │ payment.succeeded
       ▼
┌─────────────┐
│ Kalshi Agent│
└──────┬──────┘
       │ Verify payment
       ▼
┌─────────────┐
│   Kalshi    │
└──────┬──────┘
       │ Execute trade
       ▼
┌─────────────┐
│    User     │
└─────────────┘
   Trade complete
```

---

## 📚 Resources

- **Stripe API**: https://stripe.com/docs/api
- **Kalshi API**: https://trading-api.readme.io/reference/getting-started
- **ASI One**: https://uagents.fetch.ai/docs/examples/asi-1
- **Agentverse**: https://agentverse.ai/
- **DeltaV**: https://deltav.agentverse.ai/

---

## ✅ Deployment Checklist

- [ ] Stripe account created
- [ ] Stripe API keys obtained
- [ ] Stripe webhooks configured
- [ ] Kalshi account created
- [ ] Kalshi credentials saved
- [ ] Environment variables set
- [ ] Local tests passing
- [ ] Agent uploaded to Agentverse
- [ ] Agent deployed successfully
- [ ] Tested on DeltaV
- [ ] Monitoring configured
- [ ] Production keys ready (if going live)

---

## 🎉 Summary

You now have a fully functional Kalshi trading agent with:

✅ Stripe payment integration
✅ Real money trading capability
✅ ASI One compatibility
✅ DeltaV integration
✅ Automated trading system
✅ Secure payment verification
✅ Designated markets support

Ready to deploy and start trading!
