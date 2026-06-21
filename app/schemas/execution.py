from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any


class TradeDecision(BaseModel):
    ticker: str
    market_question: str

    recommendation: Literal["YES", "NO", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    fair_probability: float = Field(ge=0.0, le=1.0)
    edge: float

    current_yes_price: float = Field(gt=0.0, lt=1.0)

    max_order_dollars: float = 5.00
    dry_run: bool = True

    reasoning: Optional[str] = None


class ExecutionResult(BaseModel):
    ticker: str
    action_taken: Literal["BUY_YES", "BUY_NO", "HOLD", "REJECTED"]
    dry_run: bool

    approved: bool
    reason: str

    order_payload: Optional[Dict[str, Any]] = None
    kalshi_response: Optional[Dict[str, Any]] = None

    estimated_contracts: Optional[int] = None
    estimated_cost_dollars: Optional[float] = None