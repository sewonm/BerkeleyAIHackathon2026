# ASI One Stripe Agent - Quick Reference

Quick reference for using the Kalshi Trading Agent with ASI One's Stripe agent.

---

## ⚡ Key Changes

**Before:** Direct Stripe API integration
**After:** ASI One Stripe agent communication

**No API keys needed!** ✨

---

## 🔑 Environment Variables

### Required
```bash
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true
```

### Optional
```bash
# Has default - only set if using custom Stripe agent
ASI_ONE_STRIPE_AGENT_ADDRESS=agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5
```

---

## 🚀 Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with Kalshi credentials only

# 2. Run agent
cd uagents_deploy
python standalone_kalshi_agent.py

# 3. Deploy to Agentverse
# Upload standalone_kalshi_agent.py
# Set Kalshi credentials
# Deploy and test on DeltaV
```

---

## 📋 Payment Flow

```
User Request
    ↓
Kalshi Agent (sends payment request)
    ↓
ASI One Stripe Agent (at asi1.ai/ai/stripe)
    ↓
Payment URL sent to user
    ↓
User completes payment
    ↓
Stripe Agent confirms payment
    ↓
Kalshi Agent executes trade
    ↓
User receives confirmation
```

---

## 💬 Example Usage

### Via DeltaV

**User:**
```
Buy 10 YES contracts on KXPRESI-2024 at 52 cents with payment
```

**Agent sends to Stripe Agent:**
```json
{
  "action": "create_payment",
  "amount": 5.20,
  "description": "Kalshi Trade - KXPRESI-2024"
}
```

**User receives payment URL and completes payment**

**Trade executes automatically**

---

## 🔧 Technical Details

### Class: `ASIOneStripeAgentClient`

**Location:** `uagents_deploy/standalone_kalshi_agent.py`

**Key Methods:**
- `create_payment_request()` - Request payment from Stripe agent
- `update_payment_status()` - Update status from response
- `is_payment_succeeded()` - Check if payment completed

**Stripe Agent Address:**
```
agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5
```

---

## ✅ Checklist

### Setup
- [ ] Remove old Stripe API keys from `.env`
- [ ] Add Kalshi credentials to `.env`
- [ ] Optional: Set custom Stripe agent address

### Testing
- [ ] Run agent locally
- [ ] Verify Stripe agent connection in logs
- [ ] Test trade request without payment
- [ ] Test trade request with payment

### Deployment
- [ ] Upload to Agentverse
- [ ] Set environment variables
- [ ] Deploy agent
- [ ] Test on DeltaV
- [ ] Verify payment flow works

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No response from Stripe agent | Check `ASI_ONE_STRIPE_AGENT_ADDRESS` |
| Payment not confirmed | Ensure user completed payment |
| Trade not executing | Check Kalshi credentials |
| Agent not starting | Verify all required env vars set |

---

## 📚 Documentation

- **Full Guide:** [ASI_ONE_STRIPE_AGENT_INTEGRATION.md](ASI_ONE_STRIPE_AGENT_INTEGRATION.md)
- **Implementation:** [ASI_ONE_IMPLEMENTATION_SUMMARY.md](ASI_ONE_IMPLEMENTATION_SUMMARY.md)
- **Deployment:** [STRIPE_KALSHI_DEPLOYMENT.md](STRIPE_KALSHI_DEPLOYMENT.md)

---

## 🎯 Key Benefits

✅ No API keys required
✅ Simplified configuration
✅ Native ASI One integration
✅ Works with DeltaV
✅ Agent-to-agent messaging
✅ Secure by default

---

## 📞 Support

- **ASI One Docs:** https://uagents.fetch.ai/docs/examples/asi-1
- **Stripe Agent:** https://asi1.ai/ai/stripe
- **Agentverse:** https://agentverse.ai/
- **DeltaV:** https://deltav.agentverse.ai/

---

**Ready to trade with ASI One! 🚀**
