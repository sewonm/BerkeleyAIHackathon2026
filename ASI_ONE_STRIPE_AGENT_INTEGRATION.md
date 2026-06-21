# ASI One Stripe Agent Integration Guide

Complete guide for using the Kalshi Trading Agent with ASI One's Stripe agent for payment processing.

---

## 🎯 Overview

The Kalshi Trading Agent now integrates with **ASI One's Stripe agent** (`https://asi1.ai/ai/stripe`) for payment processing using **agent-to-agent communication** instead of direct API integration.

### Key Benefits

✅ **No API Keys Required** - Uses agent-to-agent messaging
✅ **Native ASI One Integration** - Works seamlessly with DeltaV
✅ **Simplified Setup** - No Stripe API configuration needed
✅ **Decentralized Payments** - Leverages ASI One ecosystem
✅ **Real Money Trades** - Execute Kalshi trades with verified payments

---

## 🏗️ Architecture

### Agent-to-Agent Communication

```
┌─────────────┐
│    User     │ (DeltaV)
└──────┬──────┘
       │ Request trade
       ▼
┌─────────────────────┐
│  Kalshi Agent       │
└──────┬──────────────┘
       │ Request payment
       ▼
┌─────────────────────┐
│ ASI One Stripe      │ (asi1.ai/ai/stripe)
│ Agent               │
└──────┬──────────────┘
       │ Payment URL
       ▼
┌─────────────┐
│    User     │ Complete payment
└──────┬──────┘
       │ Payment confirmed
       ▼
┌─────────────────────┐
│ ASI One Stripe      │
│ Agent               │
└──────┬──────────────┘
       │ Payment success
       ▼
┌─────────────────────┐
│  Kalshi Agent       │
└──────┬──────────────┘
       │ Execute trade
       ▼
┌─────────────┐
│   Kalshi    │
└─────────────┘
```

### Components

1. **Kalshi Trading Agent** (`standalone_kalshi_agent.py`)
   - Receives trade requests from users
   - Sends payment requests to Stripe agent
   - Executes trades on Kalshi

2. **ASI One Stripe Agent** (`asi1.ai/ai/stripe`)
   - Handles payment processing
   - Creates Stripe Checkout sessions
   - Confirms payment completion

3. **User** (via DeltaV or direct agent communication)
   - Requests trades
   - Completes payments
   - Receives trade confirmations

---

## 🔧 Implementation

### ASIOneStripeAgentClient Class

The new `ASIOneStripeAgentClient` replaces the direct Stripe API integration:

```python
class ASIOneStripeAgentClient:
    """
    Client for communicating with ASI One Stripe Agent
    """

    def __init__(self, agent_context: Optional[Context] = None):
        # ASI One Stripe Agent address
        self.stripe_agent_address = os.getenv(
            "ASI_ONE_STRIPE_AGENT_ADDRESS",
            "agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5"
        )

        self.context = agent_context
        self.pending_payments = {}
```

### Key Methods

#### 1. `create_payment_request(ctx, amount, description, metadata)`

Sends payment request to ASI One Stripe agent:

```python
async def create_payment_request(
    self,
    ctx: Context,
    amount: float,
    description: str,
    metadata: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Request payment from user via ASI One Stripe Agent"""

    payment_request = {
        "action": "create_payment",
        "amount": amount,
        "currency": "usd",
        "description": description,
        "metadata": metadata or {},
        "source": "kalshi_trading_agent",
    }

    # Send message to Stripe agent
    message = ChatMessage(
        content=[TextContent(text=json.dumps(payment_request))]
    )
    await ctx.send(self.stripe_agent_address, message)

    return request_id
```

#### 2. `update_payment_status(request_id, status, payment_data)`

Updates payment status when receiving response from Stripe agent:

```python
def update_payment_status(
    self,
    request_id: str,
    status: str,
    payment_data: Optional[Dict[str, Any]] = None
):
    """Update payment status when receiving response from Stripe agent"""

    self.pending_payments[request_id]["status"] = status
    self.pending_payments[request_id]["data"] = payment_data
```

#### 3. `is_payment_succeeded(request_id)`

Checks if payment has succeeded:

```python
def is_payment_succeeded(self, request_id: str) -> bool:
    """Check if payment has succeeded"""

    payment = self.pending_payments.get(request_id)
    return payment and payment.get("status") == "succeeded"
```

---

## 📋 Message Handlers

### Stripe Agent Response Handler

Handles responses from the ASI One Stripe agent:

```python
@execution_protocol.on_message(model=ChatMessage)
async def handle_stripe_agent_response(ctx: Context, sender: str, msg: ChatMessage):
    """Handle responses from ASI One Stripe agent"""

    # Check if message is from Stripe agent
    if sender != stripe_client.stripe_agent_address:
        return

    # Parse response
    response_data = json.loads(response_text)

    # Update payment status
    request_id = response_data.get("request_id")
    status = response_data.get("status")
    payment_url = response_data.get("payment_url")

    stripe_client.update_payment_status(
        request_id=request_id,
        status=status,
        payment_data=response_data
    )
```

---

## 🚀 Setup & Configuration

### Environment Variables

Only one environment variable is needed:

```bash
# ASI One Stripe Agent Address (optional - has default)
ASI_ONE_STRIPE_AGENT_ADDRESS=agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5
```

**Default address**: The agent uses a default address for the ASI One Stripe agent, so this variable is optional.

### No API Keys Required

Unlike the previous implementation, **no Stripe API keys are needed**:

- ❌ ~~STRIPE_SECRET_KEY~~
- ❌ ~~STRIPE_PUBLISHABLE_KEY~~
- ❌ ~~STRIPE_WEBHOOK_SECRET~~

All payment processing is handled through agent-to-agent communication.

---

## 💬 Usage Examples

### Example 1: Request Trade via DeltaV

**User Message:**
```
I want to buy 10 YES contracts on KXPRESI-2024 at 52 cents with payment
```

**Agent JSON Request:**
```json
{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52,
  "require_payment_verification": true
}
```

**Payment Flow:**
1. Kalshi agent calculates cost: 10 × $0.52 = $5.20
2. Kalshi agent sends payment request to Stripe agent
3. Stripe agent creates Checkout session
4. Stripe agent returns payment URL to user
5. User completes payment
6. Stripe agent confirms payment to Kalshi agent
7. Kalshi agent executes trade

### Example 2: Agent-to-Agent Communication

```python
from uagents import Agent, Context

orchestrator = Agent(name="orchestrator", seed="orch123", port=8001)

KALSHI_AGENT = "agent1q..."  # Your deployed Kalshi agent

@orchestrator.on_event("startup")
async def request_trade(ctx: Context):
    # Send trade request with payment verification
    request = KalshiOrderRequest(
        decision_id="orch-decision-1",
        market_id="KXPRESI-2024",
        action="BUY_YES",
        quantity=10,
        order_type="limit",
        limit_price=52,
        require_payment_verification=True  # Triggers Stripe agent
    )

    await ctx.send(KALSHI_AGENT, request)
```

---

## 🔄 Payment Protocol

### Payment Request Format

Sent from Kalshi agent to Stripe agent:

```json
{
  "action": "create_payment",
  "amount": 5.20,
  "currency": "usd",
  "description": "Kalshi Trade - KXPRESI-2024 - BUY_YES 10 contracts",
  "metadata": {
    "market_id": "KXPRESI-2024",
    "decision_id": "test-decision",
    "action": "BUY_YES",
    "quantity": "10"
  },
  "source": "kalshi_trading_agent"
}
```

### Payment Response Format

Expected from Stripe agent:

```json
{
  "request_id": "uuid-here",
  "status": "pending",
  "payment_url": "https://checkout.stripe.com/pay/...",
  "amount": 5.20,
  "currency": "usd"
}
```

### Payment Confirmation Format

Sent from Stripe agent after payment:

```json
{
  "request_id": "uuid-here",
  "status": "succeeded",
  "amount": 5.20,
  "payment_id": "pi_1234567890",
  "timestamp": "2026-06-20T10:30:00Z"
}
```

---

## 🧪 Testing

### Local Testing

```bash
# Run the agent
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
Stripe integration: ASI One Agent Mode
Stripe Agent Address: agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5
Logged in to Kalshi successfully
Account balance: $10000.00
```

### Test Payment Request

Create a test agent to send payment requests:

```python
from uagents import Agent, Context

test_agent = Agent(name="test", seed="test123", port=9000)

KALSHI_AGENT = "agent1q..."  # Your Kalshi agent address

@test_agent.on_event("startup")
async def test_payment(ctx: Context):
    request = KalshiOrderRequest(
        decision_id="test",
        market_id="KXPRESI-2024",
        action="BUY_YES",
        quantity=10,
        limit_price=52,
        require_payment_verification=True
    )

    await ctx.send(KALSHI_AGENT, request)

test_agent.run()
```

---

## 🌐 Deployment to Agentverse

### Step 1: Upload Agent

1. Go to https://agentverse.ai/
2. Create new agent
3. Select "Agent Chat Protocol (ASI) - Discoverable"
4. Upload `uagents_deploy/standalone_kalshi_agent.py`

### Step 2: Set Environment Variables

```bash
# Required
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password
KALSHI_USE_DEMO=true

# Optional (has default)
ASI_ONE_STRIPE_AGENT_ADDRESS=agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5
```

### Step 3: Deploy

1. Click "Deploy"
2. Wait for green status
3. Copy agent address
4. Test on DeltaV

---

## 🔍 Differences from Direct API Integration

### Before (Direct Stripe API)

```python
# Required API keys
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Direct API calls
payment = stripe.PaymentIntent.create(amount=1000)
```

### After (ASI One Stripe Agent)

```python
# No API keys required
ASI_ONE_STRIPE_AGENT_ADDRESS=agent1q...  # Optional

# Agent-to-agent communication
request_id = await stripe_client.create_payment_request(
    ctx=ctx,
    amount=10.00,
    description="Kalshi Trade"
)
```

### Benefits

✅ **Simplified Setup** - No Stripe account or API keys needed
✅ **Decentralized** - Uses ASI One agent ecosystem
✅ **Secure** - No sensitive credentials to manage
✅ **Native Integration** - Works seamlessly with DeltaV
✅ **Scalable** - Leverages ASI One infrastructure

---

## 📊 Expected Behavior

### Successful Payment Flow

```
1. User requests trade → Kalshi Agent
2. Kalshi Agent → Payment request → Stripe Agent
3. Stripe Agent → Payment URL → User
4. User → Completes payment → Stripe
5. Stripe Agent → Payment success → Kalshi Agent
6. Kalshi Agent → Executes trade → Kalshi
7. Kalshi Agent → Trade result → User
```

### Failed Payment Flow

```
1. User requests trade → Kalshi Agent
2. Kalshi Agent → Payment request → Stripe Agent
3. Stripe Agent → Payment URL → User
4. User → Cancels payment
5. Stripe Agent → Payment failed → Kalshi Agent
6. Kalshi Agent → Error message → User
```

---

## 🐛 Troubleshooting

### Issue: "No response from Stripe agent"

**Possible Causes:**
- Stripe agent address incorrect
- Stripe agent not available
- Network issues

**Fix:**
1. Verify `ASI_ONE_STRIPE_AGENT_ADDRESS`
2. Check agent is discoverable: https://asi1.ai/ai/stripe
3. Test connectivity on DeltaV

### Issue: "Payment not confirmed"

**Possible Causes:**
- User didn't complete payment
- Payment callback not received
- Timeout

**Fix:**
1. Ask user to complete payment
2. Check Stripe agent logs
3. Retry payment request

---

## 📚 Resources

- **ASI One Docs**: https://uagents.fetch.ai/docs/examples/asi-1
- **ASI One Stripe Agent**: https://asi1.ai/ai/stripe
- **Agentverse**: https://agentverse.ai/
- **DeltaV**: https://deltav.agentverse.ai/
- **Kalshi API**: https://trading-api.readme.io/

---

## ✨ Summary

The Kalshi Trading Agent now uses **ASI One's Stripe agent** for payment processing:

✅ **Agent-to-agent communication** instead of direct API
✅ **No API keys required** - simplified setup
✅ **Native ASI One integration** - works with DeltaV
✅ **Real money trades** - executes on Kalshi with verified payments
✅ **Decentralized payments** - leverages ASI ecosystem

**Ready to deploy and start trading with ASI One! 🚀**
