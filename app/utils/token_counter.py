"""Token counting utilities"""


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string.

    For the MVP, we use a simple approximation:
    - Try to use tiktoken if available
    - Fall back to word count * 1.3 as an approximation

    Args:
        text: The text to count tokens for

    Returns:
        Approximate token count
    """
    try:
        # Try to use tiktoken if installed
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        return len(encoding.encode(text))
    except ImportError:
        # Fall back to word-based approximation
        # Average English text: ~1.3 tokens per word
        words = text.split()
        return int(len(words) * 1.3)
