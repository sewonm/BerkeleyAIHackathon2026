"""Compression metrics and utilities"""


def calculate_compression_ratio(raw_tokens: int, compressed_tokens: int) -> float:
    """
    Calculate the compression ratio.

    Args:
        raw_tokens: Number of tokens before compression
        compressed_tokens: Number of tokens after compression

    Returns:
        Compression ratio (raw / compressed)
    """
    if compressed_tokens == 0:
        return 0.0

    return raw_tokens / compressed_tokens


def format_compression_stats(raw_tokens: int, compressed_tokens: int) -> dict:
    """
    Format compression statistics for reporting.

    Args:
        raw_tokens: Number of tokens before compression
        compressed_tokens: Number of tokens after compression

    Returns:
        Dictionary with formatted statistics
    """
    ratio = calculate_compression_ratio(raw_tokens, compressed_tokens)
    tokens_saved = raw_tokens - compressed_tokens
    percent_saved = (tokens_saved / raw_tokens * 100) if raw_tokens > 0 else 0.0

    return {
        "raw_tokens": raw_tokens,
        "compressed_tokens": compressed_tokens,
        "compression_ratio": round(ratio, 2),
        "tokens_saved": tokens_saved,
        "percent_saved": round(percent_saved, 1)
    }
