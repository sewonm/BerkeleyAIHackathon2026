"""Deduplication utilities for evidence chunks"""

from typing import List
from difflib import SequenceMatcher


def similarity_ratio(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two text strings.

    Args:
        text1: First text string
        text2: Second text string

    Returns:
        Similarity ratio between 0 and 1
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def deduplicate_chunks(chunks: List[dict], similarity_threshold: float = 0.85) -> List[dict]:
    """
    Remove near-duplicate chunks based on text similarity.

    Strategy:
    - Keep the chunk with the higher score when duplicates are found
    - Use SequenceMatcher to detect near-identical text

    Args:
        chunks: List of chunk dictionaries with 'text' and 'score' keys
        similarity_threshold: Similarity threshold for considering chunks as duplicates

    Returns:
        Deduplicated list of chunks
    """
    if not chunks:
        return []

    # Sort by score (descending) so we keep higher-scored chunks first
    sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)

    kept_chunks = []
    seen_texts = []

    for chunk in sorted_chunks:
        chunk_text = chunk.get('text', '')

        # Check if this chunk is similar to any already-kept chunk
        is_duplicate = False
        for seen_text in seen_texts:
            if similarity_ratio(chunk_text, seen_text) >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept_chunks.append(chunk)
            seen_texts.append(chunk_text)

    return kept_chunks
