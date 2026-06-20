"""LLM service wrapper - PLACEHOLDER"""


class LLMService:
    """
    Service wrapper for LLM API calls.

    TODO: Implement LLM integration (OpenAI, Anthropic, etc.)
    TODO: Features to implement:
    - Chat completions
    - Structured output parsing
    - Token counting
    - Cost tracking
    - Rate limiting
    - Retry logic

    Future use cases:
    - Enhanced decision agent reasoning
    - Evidence summarization
    - Market analysis
    - Natural language queries
    - Report generation

    For MVP, the decision agent uses deterministic rules.
    Later, this service will power LLM-based decision making.
    """

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        """
        Initialize LLM service.

        Args:
            api_key: LLM API key (optional for MVP)
            model: Model to use (not used in MVP)
        """
        self.api_key = api_key
        self.model = model
        print(f"[LLMService] PLACEHOLDER - Not implemented in MVP (model: {model})")

    def chat_completion(self, messages: list, temperature: float = 0.7):
        """TODO: Generate chat completion"""
        raise NotImplementedError("LLM integration not implemented yet")

    def structured_output(self, messages: list, schema: dict):
        """TODO: Generate structured output matching schema"""
        raise NotImplementedError("LLM integration not implemented yet")

    def count_tokens(self, text: str):
        """TODO: Count tokens for cost estimation"""
        raise NotImplementedError("LLM integration not implemented yet")
