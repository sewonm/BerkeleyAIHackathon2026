import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# This file is run from uagents_deploy/, so we manually add the repo root.
# That allows imports like app.schemas.execution and app.services.kalshi_executor.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Load .env before importing app services that read environment variables.
load_dotenv(REPO_ROOT / ".env")

from uagents import Agent, Context, Protocol, Model

from app.schemas.execution import TradeDecision
from app.services.kalshi_executor import execute_decision


AGENT_SEED = os.getenv("KALSHI_AGENT_SEED", "quorum-kalshi-executor-seed-v1")
AGENT_PORT = int(os.getenv("KALSHI_AGENT_PORT", "8007"))


class ExecutionRequest(Model):
    """
    Message expected from orchestrator/decision agent.
    """

    ticker: str
    market_question: str
    recommendation: str
    confidence: float
    fair_probability: float
    edge: float
    current_yes_price: float
    max_order_dollars: float = 5.00
    dry_run: bool = True
    reasoning: str | None = None


class ExecutionResponse(Model):
    """
    Message returned to orchestrator/decision agent.
    """

    ticker: str
    action_taken: str
    dry_run: bool
    approved: bool
    reason: str
    order_payload: dict | None = None
    kalshi_response: dict | None = None
    estimated_contracts: int | None = None
    estimated_cost_dollars: float | None = None


agent = Agent(
    name="kalshi_executor_agent",
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,
)

execution_protocol = Protocol("KalshiExecutionProtocol")


@execution_protocol.on_message(model=ExecutionRequest, replies=ExecutionResponse)
async def handle_execution_request(
    ctx: Context,
    sender: str,
    msg: ExecutionRequest,
):
    ctx.logger.info(f"Received execution request from {sender}: {msg.ticker}")

    try:
        decision = TradeDecision(
            ticker=msg.ticker,
            market_question=msg.market_question,
            recommendation=msg.recommendation,
            confidence=msg.confidence,
            fair_probability=msg.fair_probability,
            edge=msg.edge,
            current_yes_price=msg.current_yes_price,
            max_order_dollars=msg.max_order_dollars,
            dry_run=msg.dry_run,
            reasoning=msg.reasoning,
        )

        result = execute_decision(decision)

        await ctx.send(
            sender,
            ExecutionResponse(
                ticker=result.ticker,
                action_taken=result.action_taken,
                dry_run=result.dry_run,
                approved=result.approved,
                reason=result.reason,
                order_payload=result.order_payload,
                kalshi_response=result.kalshi_response,
                estimated_contracts=result.estimated_contracts,
                estimated_cost_dollars=result.estimated_cost_dollars,
            ),
        )

    except Exception as e:
        ctx.logger.exception("Kalshi execution failed")

        await ctx.send(
            sender,
            ExecutionResponse(
                ticker=msg.ticker,
                action_taken="REJECTED",
                dry_run=msg.dry_run,
                approved=False,
                reason=f"Executor error: {str(e)}",
            ),
        )


agent.include(execution_protocol)


if __name__ == "__main__":
    print(f"Repo root added to Python path: {REPO_ROOT}")
    print(f"Kalshi Executor Agent address: {agent.address}")
    print(f"Kalshi Executor Agent port: {AGENT_PORT}")
    print("Default mode: dry-run unless request says otherwise.")
    agent.run()