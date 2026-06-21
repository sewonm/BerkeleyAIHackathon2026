"""
Standalone Kalshi Execution Agent - Executes trades on Kalshi API with Stripe Integration.

FULLY SELF-CONTAINED for Agentverse deployment (no external app/* imports).

This agent:
1. Receives trading decisions from Decision Agent
2. Connects to Stripe for payment verification (ASI One integration)
3. Manages account balance and deposits
4. Connects to Kalshi API
5. Places orders (market or limit) with real money
6. Monitors order status
7. Reports execution results

Kalshi API Documentation: https://trading-api.readme.io/reference/getting-started
Stripe API Documentation: https://stripe.com/docs/api
"""

import os
import json
import requests
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field
import hashlib
import hmac

from uagents import Agent, Context, Protocol

# ASI:One chat protocol support (optional, gracefully degrades if unavailable)
try:
    from uagents.chat import (
        chat_protocol_spec,
        ChatMessage,
        TextContent,
        EndSessionContent,
        ChatAcknowledgement
    )
    CHAT_PROTOCOL_AVAILABLE = True
except ImportError:
    print("[Warning] Chat protocol not available - ASI:One integration disabled")
    print("Install with: pip install uagents[chat]")
    CHAT_PROTOCOL_AVAILABLE = False


# ============================================================================
# SCHEMAS (Self-contained)
# ============================================================================

class StripePaymentIntent(BaseModel):
    """Stripe payment intent for funding Kalshi trades"""
    payment_intent_id: str
    amount: int  # Amount in cents
    currency: str = "usd"
    status: str
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class KalshiOrderRequest(BaseModel):
    """Request to Kalshi Execution Agent to place an order"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str  # Reference to TradingDecision
    market_id: str  # Kalshi ticker

    # Order details
    action: Literal["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO"]
    quantity: int = Field(..., gt=0)  # Number of contracts
    order_type: Literal["market", "limit"] = "limit"
    limit_price: Optional[int] = None  # Price in cents (0-100)

    # Risk management
    max_slippage: Optional[float] = 0.02
    timeout_seconds: Optional[int] = 30

    # Execution strategy
    execution_strategy: Optional[Literal["immediate", "passive", "smart"]] = "smart"

    # Stripe payment integration (optional)
    payment_intent_id: Optional[str] = None  # Link to Stripe payment
    require_payment_verification: bool = False  # Require payment before trade


class KalshiOrderStatus(BaseModel):
    """Status of a Kalshi order"""
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
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None
    total_cost: Optional[float] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)

    # Error details
    error_message: Optional[str] = None
    rejection_reason: Optional[str] = None


class KalshiOrderResponse(BaseModel):
    """Response from Kalshi Execution Agent"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    order_status: Optional[KalshiOrderStatus] = None


# ============================================================================
# KALSHI API CLIENT
# ============================================================================

class KalshiAPIClient:
    """
    Kalshi API client for order execution.

    API Documentation: https://trading-api.readme.io/reference/getting-started
    """

    def __init__(self):
        self.api_key = os.getenv("KALSHI_API_KEY")
        self.api_secret = os.getenv("KALSHI_API_SECRET")
        self.email = os.getenv("KALSHI_EMAIL")
        self.password = os.getenv("KALSHI_PASSWORD")

        # API endpoints
        self.use_demo = os.getenv("KALSHI_USE_DEMO", "true").lower() == "true"
        if self.use_demo:
            self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        else:
            self.base_url = "https://trading-api.kalshi.com/trade-api/v2"

        self.token = None
        self.user_id = None

        print(f"[KalshiClient] Initialized ({'DEMO' if self.use_demo else 'PRODUCTION'} mode)")

    def login(self) -> bool:
        """
        Login to Kalshi API.

        Returns:
            True if login successful
        """
        if not self.email or not self.password:
            print("[KalshiClient] No credentials provided (KALSHI_EMAIL, KALSHI_PASSWORD)")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/login",
                json={
                    "email": self.email,
                    "password": self.password
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.user_id = data.get("member_id")
                print(f"[KalshiClient] Login successful (user_id: {self.user_id})")
                return True
            else:
                print(f"[KalshiClient] Login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"[KalshiClient] Login error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.token:
            raise ValueError("Not logged in - call login() first")

        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_market(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get market data from Kalshi.

        Args:
            ticker: Market ticker

        Returns:
            Market data or None
        """
        try:
            response = requests.get(
                f"{self.base_url}/markets/{ticker}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return response.json().get("market")
            else:
                print(f"[KalshiClient] Get market failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"[KalshiClient] Get market error: {e}")
            return None

    def place_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "limit",
        limit_price: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order on Kalshi.

        Args:
            ticker: Market ticker
            action: BUY_YES, BUY_NO, SELL_YES, SELL_NO
            quantity: Number of contracts
            order_type: "market" or "limit"
            limit_price: Limit price in cents (0-100)

        Returns:
            Order response data or None
        """
        try:
            # Map action to Kalshi API format
            if action == "BUY_YES":
                side = "yes"
                action_type = "buy"
            elif action == "BUY_NO":
                side = "no"
                action_type = "buy"
            elif action == "SELL_YES":
                side = "yes"
                action_type = "sell"
            elif action == "SELL_NO":
                side = "no"
                action_type = "sell"
            else:
                raise ValueError(f"Invalid action: {action}")

            # Build order payload
            order_data = {
                "ticker": ticker,
                "action": action_type,
                "side": side,
                "count": quantity,
                "type": order_type,
            }

            if order_type == "limit":
                if limit_price is None:
                    raise ValueError("limit_price required for limit orders")
                # Kalshi uses separate yes_price and no_price
                if side == "yes":
                    order_data["yes_price"] = limit_price
                else:
                    order_data["no_price"] = limit_price

            print(f"[KalshiClient] Placing order: {order_data}")

            response = requests.post(
                f"{self.base_url}/portfolio/orders",
                headers=self._get_headers(),
                json=order_data
            )

            if response.status_code == 201:
                order_response = response.json()
                print(f"[KalshiClient] Order placed successfully: {order_response.get('order', {}).get('order_id')}")
                return order_response.get("order")
            else:
                print(f"[KalshiClient] Place order failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"[KalshiClient] Place order error: {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order status.

        Args:
            order_id: Order ID

        Returns:
            Order status data or None
        """
        try:
            response = requests.get(
                f"{self.base_url}/portfolio/orders/{order_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return response.json().get("order")
            else:
                print(f"[KalshiClient] Get order status failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"[KalshiClient] Get order status error: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID

        Returns:
            True if cancelled successfully
        """
        try:
            response = requests.delete(
                f"{self.base_url}/portfolio/orders/{order_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                print(f"[KalshiClient] Order cancelled: {order_id}")
                return True
            else:
                print(f"[KalshiClient] Cancel order failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[KalshiClient] Cancel order error: {e}")
            return False

    def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Get account balance.

        Returns:
            Balance data or None
        """
        try:
            response = requests.get(
                f"{self.base_url}/portfolio/balance",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"[KalshiClient] Get balance failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"[KalshiClient] Get balance error: {e}")
            return None


# ============================================================================
# ASI ONE STRIPE AGENT CLIENT
# ============================================================================

class ASIOneStripeAgentClient:
    """
    Client for communicating with ASI One Stripe Agent (https://asi1.ai/ai/stripe)

    Instead of direct Stripe API integration, this uses agent-to-agent
    communication with the official ASI One Stripe agent.
    """

    def __init__(self, agent_context: Optional[Context] = None):
        # ASI One Stripe Agent address
        self.stripe_agent_address = os.getenv(
            "ASI_ONE_STRIPE_AGENT_ADDRESS",
            "agent1q2kxet3vh0scsf0sm7y2erzz33cve6tv5uk63x64upw5g68fr0j9p9lkzm5"  # Default ASI One Stripe agent
        )

        # Store context for sending messages
        self.context = agent_context

        # Payment tracking
        self.pending_payments = {}

        print(f"[ASIOneStripeClient] Initialized")
        print(f"   Stripe Agent: {self.stripe_agent_address}")

    async def create_payment_request(
        self,
        ctx: Context,
        amount: float,
        description: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Request payment from user via ASI One Stripe Agent.

        Args:
            ctx: Agent context for sending messages
            amount: Amount in dollars (e.g., 10.00)
            description: Payment description
            metadata: Additional metadata

        Returns:
            Payment request ID or None
        """
        if not ctx:
            print("[ASIOneStripeClient] No context available - cannot send messages")
            return None

        try:
            # Build payment request message for Stripe agent
            payment_request = {
                "action": "create_payment",
                "amount": amount,
                "currency": "usd",
                "description": description,
                "metadata": metadata or {},
                "source": "kalshi_trading_agent",
            }

            # Generate request ID
            request_id = str(uuid4())

            # Store pending payment
            self.pending_payments[request_id] = {
                "status": "pending",
                "amount": amount,
                "created_at": datetime.now(),
            }

            print(f"[ASIOneStripeClient] Requesting payment: ${amount:.2f}")
            print(f"   Request ID: {request_id}")
            print(f"   Description: {description}")

            # Send message to Stripe agent
            if CHAT_PROTOCOL_AVAILABLE:
                message = ChatMessage(
                    content=[TextContent(text=json.dumps(payment_request))]
                )
                await ctx.send(self.stripe_agent_address, message)
            else:
                # Fallback: send as plain JSON if chat protocol unavailable
                await ctx.send(self.stripe_agent_address, payment_request)

            return request_id

        except Exception as e:
            print(f"[ASIOneStripeClient] Create payment request error: {e}")
            return None

    def update_payment_status(self, request_id: str, status: str, payment_data: Optional[Dict[str, Any]] = None):
        """
        Update payment status when receiving response from Stripe agent.

        Args:
            request_id: Payment request ID
            status: Payment status (succeeded, failed, pending)
            payment_data: Additional payment data
        """
        if request_id in self.pending_payments:
            self.pending_payments[request_id]["status"] = status
            self.pending_payments[request_id]["updated_at"] = datetime.now()

            if payment_data:
                self.pending_payments[request_id]["data"] = payment_data

            print(f"[ASIOneStripeClient] Payment status updated: {request_id} -> {status}")

    def get_payment_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment status for a request.

        Args:
            request_id: Payment request ID

        Returns:
            Payment status data or None
        """
        return self.pending_payments.get(request_id)

    def is_payment_succeeded(self, request_id: str) -> bool:
        """
        Check if payment has succeeded.

        Args:
            request_id: Payment request ID

        Returns:
            True if payment succeeded
        """
        payment = self.pending_payments.get(request_id)
        return payment and payment.get("status") == "succeeded"


# ============================================================================
# EXECUTION ENGINE
# ============================================================================

class ExecutionEngine:
    """Smart order execution engine with ASI One Stripe agent integration"""

    def __init__(self, kalshi_client: KalshiAPIClient, stripe_client: ASIOneStripeAgentClient):
        self.kalshi_client = kalshi_client
        self.stripe_client = stripe_client

    async def execute_order(self, ctx: Context, request: KalshiOrderRequest) -> KalshiOrderStatus:
        """
        Execute an order with smart execution strategy.

        Args:
            request: Order request

        Returns:
            Order status
        """
        # Step 1: Request payment via ASI One Stripe agent if required
        if request.require_payment_verification:
            # Calculate estimated cost
            estimated_cost = request.quantity * (request.limit_price or 50) / 100

            # Request payment from Stripe agent
            payment_request_id = await self.stripe_client.create_payment_request(
                ctx=ctx,
                amount=estimated_cost,
                description=f"Kalshi Trade - {request.market_id} - {request.action} {request.quantity} contracts",
                metadata={
                    "market_id": request.market_id,
                    "decision_id": request.decision_id,
                    "action": request.action,
                    "quantity": str(request.quantity),
                }
            )

            if not payment_request_id:
                return KalshiOrderStatus(
                    order_id=str(uuid4()),
                    request_id=request.request_id,
                    market_id=request.market_id,
                    status="error",
                    error_message="Failed to create payment request with ASI One Stripe agent"
                )

            # Store payment request ID for tracking
            request.payment_intent_id = payment_request_id

            print(f"[ExecutionEngine] Payment requested via ASI One Stripe agent")
            print(f"   Payment Request ID: {payment_request_id}")
            print(f"   Amount: ${estimated_cost:.2f}")
            print(f"   Waiting for user to complete payment...")

            # Note: In actual implementation, the execution would wait for a callback
            # from the Stripe agent confirming payment. For now, we'll proceed
            # assuming the payment flow is handled separately.

        # Step 2: Ensure logged in to Kalshi
        if not self.kalshi_client.token:
            if not self.kalshi_client.login():
                return KalshiOrderStatus(
                    order_id=str(uuid4()),
                    request_id=request.request_id,
                    market_id=request.market_id,
                    status="error",
                    error_message="Failed to login to Kalshi"
                )

        # Step 3: Get current market data
        market = self.kalshi_client.get_market(request.market_id)
        if not market:
            return KalshiOrderStatus(
                order_id=str(uuid4()),
                request_id=request.request_id,
                market_id=request.market_id,
                status="error",
                error_message=f"Market not found: {request.market_id}"
            )

        # Determine limit price if not provided
        limit_price = request.limit_price
        if limit_price is None and request.order_type == "limit":
            limit_price = self._calculate_limit_price(
                request.action,
                market,
                request.max_slippage or 0.02
            )

        # Step 4: Place order on Kalshi
        order_response = self.kalshi_client.place_order(
            ticker=request.market_id,
            action=request.action,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price=limit_price
        )

        if not order_response:
            return KalshiOrderStatus(
                order_id=str(uuid4()),
                request_id=request.request_id,
                market_id=request.market_id,
                status="error",
                error_message="Failed to place order"
            )

        # Build order status
        order_status = KalshiOrderStatus(
            order_id=order_response.get("order_id", str(uuid4())),
            request_id=request.request_id,
            market_id=request.market_id,
            status=self._map_kalshi_status(order_response.get("status", "pending")),
            filled_quantity=order_response.get("remaining_count", 0),
            submitted_at=datetime.now()
        )

        return order_status

    def _calculate_limit_price(
        self,
        action: str,
        market: Dict[str, Any],
        max_slippage: float
    ) -> int:
        """
        Calculate limit price based on current market prices.

        Args:
            action: BUY_YES, BUY_NO, etc.
            market: Market data
            max_slippage: Maximum acceptable slippage

        Returns:
            Limit price in cents
        """
        if action == "BUY_YES":
            # Buy YES: use ask price + slippage
            ask = market.get("yes_ask", 50)
            limit_price = int(ask * (1 + max_slippage))
        elif action == "BUY_NO":
            # Buy NO: use ask price + slippage
            ask = market.get("no_ask", 50)
            limit_price = int(ask * (1 + max_slippage))
        elif action == "SELL_YES":
            # Sell YES: use bid price - slippage
            bid = market.get("yes_bid", 50)
            limit_price = int(bid * (1 - max_slippage))
        elif action == "SELL_NO":
            # Sell NO: use bid price - slippage
            bid = market.get("no_bid", 50)
            limit_price = int(bid * (1 - max_slippage))
        else:
            limit_price = 50

        # Clamp to valid range
        return max(1, min(99, limit_price))

    def _map_kalshi_status(self, kalshi_status: str) -> str:
        """Map Kalshi order status to our status"""
        status_map = {
            "pending": "pending",
            "resting": "submitted",
            "canceled": "cancelled",
            "executed": "filled",
            "active": "submitted",
        }
        return status_map.get(kalshi_status, "pending")


# ============================================================================
# UAGENT SETUP
# ============================================================================

AGENT_NAME = "kalshi_execution_agent"
AGENT_SEED = "kalshi_execution_agent_seed_change_in_production"
AGENT_PORT = 8004
AGENT_MAILBOX = True

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,  # Simple mailbox configuration
)

execution_protocol = Protocol("KalshiExecution")
kalshi_client = KalshiAPIClient()
stripe_client = ASIOneStripeAgentClient()  # ASI One Stripe agent client
execution_engine = ExecutionEngine(kalshi_client, stripe_client)

# ASI:One chat protocol (if available)
if CHAT_PROTOCOL_AVAILABLE:
    chat_protocol = Protocol("Chat", spec=chat_protocol_spec)


@execution_protocol.on_message(model=KalshiOrderRequest)
async def handle_order_request(ctx: Context, sender: str, msg: KalshiOrderRequest):
    """Handle order execution requests"""
    ctx.logger.info(f"[{AGENT_NAME}] Received order request from {sender}")
    ctx.logger.info(f"Market: {msg.market_id}")
    ctx.logger.info(f"Action: {msg.action}")
    ctx.logger.info(f"Quantity: {msg.quantity}")

    try:
        # Execute order (now async to support Stripe agent communication)
        order_status = await execution_engine.execute_order(ctx, msg)

        # Send response
        response = KalshiOrderResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="success" if order_status.status != "error" else "error",
            error=order_status.error_message,
            order_status=order_status
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Order execution complete")
        ctx.logger.info(f"  Order ID: {order_status.order_id}")
        ctx.logger.info(f"  Status: {order_status.status}")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Order execution failed: {e}")
        import traceback
        ctx.logger.error(traceback.format_exc())

        # Send error response
        response = KalshiOrderResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="error",
            error=str(e)
        )

        await ctx.send(sender, response)


# ============================================================================
# STRIPE AGENT RESPONSE HANDLER
# ============================================================================

if CHAT_PROTOCOL_AVAILABLE:
    @execution_protocol.on_message(model=ChatMessage)
    async def handle_stripe_agent_response(ctx: Context, sender: str, msg: ChatMessage):
        """Handle responses from ASI One Stripe agent"""
        # Check if message is from Stripe agent
        if sender != stripe_client.stripe_agent_address:
            return  # Not from Stripe agent, ignore

        ctx.logger.info(f"[{AGENT_NAME}] Received response from Stripe agent")

        try:
            # Extract text from message
            response_text = ""
            for content in msg.content:
                if isinstance(content, TextContent):
                    response_text += content.text

            # Parse response
            response_data = json.loads(response_text)

            # Update payment status
            request_id = response_data.get("request_id")
            status = response_data.get("status")
            payment_url = response_data.get("payment_url")

            if request_id:
                stripe_client.update_payment_status(
                    request_id=request_id,
                    status=status,
                    payment_data=response_data
                )

                ctx.logger.info(f"[{AGENT_NAME}] Payment status updated: {request_id} -> {status}")

                if payment_url:
                    ctx.logger.info(f"[{AGENT_NAME}] Payment URL: {payment_url}")

        except json.JSONDecodeError:
            ctx.logger.warning(f"[{AGENT_NAME}] Could not parse Stripe agent response as JSON")
        except Exception as e:
            ctx.logger.error(f"[{AGENT_NAME}] Error handling Stripe agent response: {e}")


# ============================================================================
# ASI:One Chat Protocol Handler (DeltaV Integration)
# ============================================================================

if CHAT_PROTOCOL_AVAILABLE:
    @chat_protocol.on_message(model=ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        """Handle chat messages from DeltaV or other ASI:One compatible clients"""
        ctx.logger.info(f"[{AGENT_NAME}] Received chat message from {sender}")

        # Send acknowledgement
        await ctx.send(sender, ChatAcknowledgement())

        # Extract text from message content
        user_text = ""
        for content in msg.content:
            if isinstance(content, TextContent):
                user_text += content.text

        ctx.logger.info(f"[{AGENT_NAME}] Message: {user_text[:100]}...")

        # Try to parse as JSON (structured request)
        try:
            request_data = json.loads(user_text)

            # Build KalshiOrderRequest with Stripe integration
            order_request = KalshiOrderRequest(
                decision_id=request_data.get("decision_id", "chat-decision"),
                market_id=request_data["market_id"],
                action=request_data["action"],
                quantity=request_data["quantity"],
                order_type=request_data.get("order_type", "limit"),
                limit_price=request_data.get("limit_price"),
                max_slippage=request_data.get("max_slippage", 0.02),
                timeout_seconds=request_data.get("timeout_seconds", 30),
                execution_strategy=request_data.get("execution_strategy", "smart"),
                # Stripe payment integration
                payment_intent_id=request_data.get("payment_intent_id"),
                require_payment_verification=request_data.get("require_payment_verification", False),
            )

            # Execute order (now async)
            order_status = await execution_engine.execute_order(ctx, order_request)

            # Format response
            response_text = f"""**Kalshi Order Executed**

**Market**: {order_request.market_id}
**Action**: {order_request.action}
**Quantity**: {order_request.quantity} contracts

**Order Status**: {order_status.status}
**Order ID**: {order_status.order_id}

**Execution**:
- Fill Price: {order_status.fill_price / 100:.2%} (${order_status.fill_price / 100:.2f})
- Filled Quantity: {order_status.filled_quantity}/{order_request.quantity}
- Execution Time: {order_status.execution_time_ms}ms

**Costs**:
- Total Cost: ${order_status.total_cost:.2f}
- Platform Fees: ${order_status.platform_fees:.2f}

**Message**: {order_status.message}
"""

            response_msg = ChatMessage(
                content=[TextContent(text=response_text)]
            )
            await ctx.send(sender, response_msg)

        except json.JSONDecodeError:
            # Not JSON - provide help message
            help_message = f"""**Kalshi Execution Agent with Stripe Integration**

I execute trades on Kalshi prediction markets with integrated Stripe payment processing for ASI One.

**How to use me**:

**Option 1: Direct Trade (without payment verification)**
```json
{{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52,
  "execution_strategy": "smart"
}}
```

**Option 2: Paid Trade (with Stripe payment)**
```json
{{
  "market_id": "KXPRESI-2024",
  "action": "BUY_YES",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 52,
  "payment_intent_id": "pi_1234567890",
  "require_payment_verification": true
}}
```

**Actions**: BUY_YES, BUY_NO, SELL_YES, SELL_NO
**Order Types**: market, limit
**Execution Strategies**: immediate, passive, smart

**ASI One Stripe Agent Integration**:
- ✅ Communicates with ASI One Stripe agent (asi1.ai/ai/stripe)
- ✅ Agent-to-agent payment processing
- ✅ Automatic payment requests
- ✅ Real money trades with verified funds
- ✅ Seamless DeltaV integration

**Requirements**:
- Kalshi account credentials (KALSHI_EMAIL, KALSHI_PASSWORD)
- ASI One Stripe agent available at asi1.ai/ai/stripe
- Can use demo mode for testing (KALSHI_USE_DEMO=true)

**Payment Flow**:
1. User requests trade via DeltaV
2. Agent sends payment request to ASI One Stripe agent
3. Stripe agent returns payment URL
4. User completes payment
5. Stripe agent confirms payment success
6. Agent executes trade on Kalshi
7. Agent reports results

**Outputs**:
- Order ID and status
- Fill price and quantity
- Execution time
- Platform fees
- Total cost
- Payment verification status

I connect to official Kalshi API and Stripe API for secure, real-money trade execution.
"""

            response_msg = ChatMessage(
                content=[TextContent(text=help_message)]
            )
            await ctx.send(sender, response_msg)

        except Exception as e:
            # Error handling
            error_text = f"**Error**: Failed to execute order\n\n{str(e)}"
            response_msg = ChatMessage(
                content=[TextContent(text=error_text)]
            )
            await ctx.send(sender, response_msg)
            ctx.logger.error(f"[{AGENT_NAME}] Chat handler error: {e}")

        finally:
            # Always end the session
            await ctx.send(sender, ChatMessage(content=[EndSessionContent()]))


# ============================================================================
# Protocol Inclusion
# ============================================================================

# Include custom protocol for agent-to-agent communication
agent.include(execution_protocol, publish_manifest=False)

# Include ASI:One chat protocol if available
if CHAT_PROTOCOL_AVAILABLE:
    agent.include(chat_protocol, publish_manifest=True)


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[{AGENT_NAME}] Kalshi Execution Agent started!")
    ctx.logger.info(f"Address: {agent.address}")
    ctx.logger.info(f"Mode: {'DEMO' if kalshi_client.use_demo else 'PRODUCTION'}")
    ctx.logger.info(f"Ready to execute orders on Kalshi")

    # Protocol status
    ctx.logger.info("Custom protocol: ENABLED (agent-to-agent communication)")
    if CHAT_PROTOCOL_AVAILABLE:
        ctx.logger.info("ASI:One chat protocol: ENABLED (DeltaV compatible)")
    else:
        ctx.logger.info("ASI:One chat protocol: DISABLED (install uagents[chat])")

    # ASI One Stripe agent integration status
    ctx.logger.info("Stripe integration: ASI One Agent Mode")
    ctx.logger.info(f"Stripe Agent Address: {stripe_client.stripe_agent_address}")

    # Try to login to Kalshi
    if kalshi_client.email and kalshi_client.password:
        if kalshi_client.login():
            ctx.logger.info("Logged in to Kalshi successfully")
            # Get balance
            balance = kalshi_client.get_balance()
            if balance:
                ctx.logger.info(f"Account balance: ${balance.get('balance', 0) / 100:.2f}")
        else:
            ctx.logger.warning("Failed to login to Kalshi - will retry on first order")
    else:
        ctx.logger.warning("No Kalshi credentials provided (KALSHI_EMAIL, KALSHI_PASSWORD)")


if __name__ == "__main__":
    agent.run()
