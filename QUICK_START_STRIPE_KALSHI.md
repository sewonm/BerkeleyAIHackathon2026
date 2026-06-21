# Quick Start: Stripe-Kalshi Trading Agent

Get started with the Stripe-integrated Kalshi trading agent in 5 minutes.

---

## ⚡ Super Quick Start

```bash
# 1. Set up environment
cp .env.example .env
nano .env  # Add your credentials

# 2. Test integration
python test_stripe_kalshi_integration.py

# 3. Run automated trader
python designated_markets_trader.py
```

---

## 🔑 Required Credentials

### Stripe (Get from https://stripe.com)
```bash
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_ASI_ONE_MODE=true
```

### Kalshi (Get from https://kalshi.com)
```bash
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true  # Use demo for testing
```

---

## 📋 Usage Modes

### Mode 1: Local Testing

Test the integration locally:

```bash
python test_stripe_kalshi_integration.py
```

**What it does:**
- Creates Stripe payment intent
- Verifies payment status
- Connects to Kalshi
- Tests trade execution

### Mode 2: Automated Trading

Run automated trading on designated markets:

```bash
python designated_markets_trader.py
```

**What it does:**
- Monitors designated markets
- Makes trading decisions
- Processes Stripe payments
- Executes trades on Kalshi

### Mode 3: Agent Deployment

Deploy to Agentverse for ASI One:

1. Go to https://agentverse.ai/
2. Upload `uagents_deploy/standalone_kalshi_agent.py`
3. Set environment variables
4. Deploy and test on DeltaV

---

## 🎯 Test Card

Use this for Stripe testing:

```
Card Number: 4242 4242 4242 4242
Expiry: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

---

## 📊 Example Requests

### Direct Trade (No Payment)

```json
{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52
}
```

### Paid Trade (With Stripe)

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

---

## ✅ Quick Checklist

Before running:
- [ ] `.env` file created with credentials
- [ ] Stripe account active (test mode)
- [ ] Kalshi account active (demo mode)
- [ ] Dependencies installed (`pip install requests pydantic uagents python-dotenv`)

To test:
- [ ] Run `test_stripe_kalshi_integration.py`
- [ ] Verify payment creation works
- [ ] Verify Kalshi login works
- [ ] Execute test trade

To deploy:
- [ ] Upload to Agentverse
- [ ] Set environment variables
- [ ] Deploy agent
- [ ] Test on DeltaV

---

## 🚨 Common Issues

### "Stripe integration: DISABLED"
→ Set `STRIPE_SECRET_KEY` in `.env`

### "Failed to login to Kalshi"
→ Check `KALSHI_EMAIL` and `KALSHI_PASSWORD`

### "Payment verification failed"
→ Complete payment with test card first

### "Market not found"
→ Use valid market ID (e.g., "KXPRESI-2024")

---

## 📚 Documentation

- **Full Integration Guide**: [KALSHI_STRIPE_INTEGRATION.md](uagents_deploy/KALSHI_STRIPE_INTEGRATION.md)
- **Deployment Guide**: [STRIPE_KALSHI_DEPLOYMENT.md](STRIPE_KALSHI_DEPLOYMENT.md)
- **Implementation Summary**: [STRIPE_INTEGRATION_SUMMARY.md](STRIPE_INTEGRATION_SUMMARY.md)

---

## 🎉 Ready to Trade!

Your agent can now:
- ✅ Accept Stripe payments
- ✅ Verify payment completion
- ✅ Execute Kalshi trades
- ✅ Work with ASI One/DeltaV
- ✅ Automate designated markets

**Start trading in demo mode, then switch to production when ready!**
