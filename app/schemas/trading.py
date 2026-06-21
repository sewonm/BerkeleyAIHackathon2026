"""
Trading schemas for Decision Agent and Kalshi Execution Agent.

These schemas define the data structures for:
1. Decision Agent: Analyzes compressed context → makes trading decision
2. Kalshi Execution Agent: Takes decision → executes trades on Kalshi
"""

from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


# ============================================================================
# DECISION AGENT SCHEMAS
# ============================================================================

class TradingDecisionRequest(BaseModel):
    """Request to Decision Agent for a trading decision"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    market_id: str
    market_question: str
    resolution_criteria: str

    # Current market state
    current_yes_price: float = Field(..., ge=0.0, le=1.0)
    current_no_price: float = Field(..., ge=0.0, le=1.0)
    volume_24h: Optional[float] = None
    liquidity: Optional[float] = None

    # Compressed context from Compression Agent
    compressed_context: str
    compression_metrics: Optional[Dict[str, Any]] = None

    # Evidence summary (optional, from Compression Agent)
    top_yes_evidence: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    top_no_evidence: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    contradictions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # User constraints
    max_position_size: Optional[float] = 100.0  # Max $ to trade
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = "moderate"
    existing_position: Optional[float] = None  # Current position in market (+ for YES, - for NO)


class TradingDecision(BaseModel):
    """Decision output from Decision Agent"""
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    market_id: str

    # Core decision
    action: Literal["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO", "HOLD"]
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Position sizing
    suggested_position_size: float = Field(..., ge=0.0)  # $ amount
    suggested_contracts: Optional[int] = None  # Number of contracts

    # Pricing
    estimated_fair_value: float = Field(..., ge=0.0, le=1.0)  # What agent thinks YES price should be
    price_limit: Optional[float] = None  # Max price willing to pay (for buys) or min for sells

    # Reasoning
    reasoning: str
    key_factors: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    # Expected value calculation
    expected_value: Optional[float] = None
    edge: Optional[float] = None  # Estimated edge vs current price

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)


class TradingDecisionResponse(BaseModel):
    """Response from Decision Agent"""
    request_id: str
    market_id: str
    status: Literal["success", "error"]
    error: Optional[str] = None
    decision: Optional[TradingDecision] = None


# ============================================================================
# KALSHI EXECUTION AGENT SCHEMAS
# ============================================================================

class KalshiOrderRequest(BaseModel):
    """Request to Kalshi Execution Agent to place an order"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str  # Reference to TradingDecision
    market_id: str

    # Order details
    action: Literal["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO"]
    quantity: int = Field(..., gt=0)  # Number of contracts
    order_type: Literal["market", "limit"] = "limit"
    limit_price: Optional[float] = None  # Required for limit orders

    # Risk management
    max_slippage: Optional[float] = 0.02  # Max acceptable slippage (2%)
    timeout_seconds: Optional[int] = 30  # Order timeout

    # Execution strategy
    execution_strategy: Optional[Literal["immediate", "passive", "smart"]] = "smart"


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
# PORTFOLIO MANAGEMENT
# ============================================================================

class PortfolioPosition(BaseModel):
    """Current position in a market"""
    market_id: str
    market_question: str

    # Position details
    yes_contracts: int = 0
    no_contracts: int = 0
    net_position: int = 0  # positive = net YES, negative = net NO

    # Cost basis
    total_cost: float = 0.0
    average_entry_price: Optional[float] = None

    # Current value
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0

    # Metadata
    opened_at: datetime
    last_updated: datetime = Field(default_factory=datetime.now)


class Portfolio(BaseModel):
    """Overall portfolio state"""
    portfolio_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str

    # Positions
    positions: List[PortfolioPosition] = Field(default_factory=list)

    # Account summary
    total_value: float = 0.0
    cash_balance: float = 0.0
    buying_power: float = 0.0

    # Performance
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0

    # Risk metrics
    total_exposure: float = 0.0
    concentration_risk: Optional[float] = None  # Max % in single position

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


# ============================================================================
# KALSHI API MODELS (from Kalshi API docs)
# ============================================================================

class KalshiMarket(BaseModel):
    """Kalshi market data"""
    ticker: str
    event_ticker: str
    title: str
    subtitle: Optional[str] = None
    status: str
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None
    last_price: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    close_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None


class KalshiOrder(BaseModel):
    """Kalshi order structure"""
    order_id: Optional[str] = None
    ticker: str
    action: Literal["buy", "sell"]
    side: Literal["yes", "no"]
    count: int
    type: Literal["market", "limit"]
    yes_price: Optional[int] = None  # Price in cents (0-100)
    no_price: Optional[int] = None
    expiration_ts: Optional[int] = None
    status: Optional[str] = None
    created_time: Optional[datetime] = None


class KalshiBalance(BaseModel):
    """Kalshi account balance"""
    balance: int  # Balance in cents
    payout: int  # Pending payouts in cents
