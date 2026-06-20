"""Kalshi API service wrapper - PLACEHOLDER"""


class KalshiService:
    """
    Service wrapper for Kalshi API.

    TODO: Implement Kalshi API integration
    TODO: Features to implement:
    - Authentication with API key
    - Get market data
    - Get market prices
    - Get order book
    - Place orders (demo and live)
    - Cancel orders
    - Get account balance
    - Get market history

    Future use cases:
    - Fetch current market prices
    - Get resolution criteria
    - Place demo trades
    - Monitor order execution

    For MVP, this is a placeholder. No API key required.
    No real trading in MVP.
    """

    def __init__(self, api_key: str = None, environment: str = "demo"):
        """
        Initialize Kalshi service.

        Args:
            api_key: Kalshi API key (optional for MVP)
            environment: 'demo' or 'production' (not used in MVP)
        """
        self.api_key = api_key
        self.environment = environment
        print(f"[KalshiService] PLACEHOLDER - Not implemented in MVP (env: {environment})")

    def get_market(self, market_id: str):
        """TODO: Get market data"""
        raise NotImplementedError("Kalshi integration not implemented yet")

    def get_market_price(self, market_id: str):
        """TODO: Get current market price"""
        raise NotImplementedError("Kalshi integration not implemented yet")

    def place_order(self, market_id: str, side: str, quantity: int, price: float):
        """TODO: Place an order"""
        raise NotImplementedError("Kalshi integration not implemented yet")

    def cancel_order(self, order_id: str):
        """TODO: Cancel an order"""
        raise NotImplementedError("Kalshi integration not implemented yet")

    def get_balance(self):
        """TODO: Get account balance"""
        raise NotImplementedError("Kalshi integration not implemented yet")
