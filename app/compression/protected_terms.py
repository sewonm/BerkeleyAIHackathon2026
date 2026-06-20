"""Extract protected terms from market data"""

import re
from typing import List, Set

from app.schemas.market import Market


def extract_protected_terms(market: Market) -> List[str]:
    """
    Extract important terms that should be preserved during compression.

    Protected terms include:
    - Explicit protected_terms from the market
    - Key words from the market title
    - Key words from the market question
    - Numbers and dates found in market fields
    - Named entities (capitalized phrases)

    Args:
        market: The market to extract terms from

    Returns:
        List of protected terms (deduplicated and lowercased)
    """
    protected = set()

    # Add explicit protected terms
    for term in market.protected_terms:
        protected.add(term.lower().strip())

    # Extract key words from title (remove common words)
    title_words = extract_key_words(market.title)
    protected.update(title_words)

    # Extract key words from question
    question_words = extract_key_words(market.question)
    protected.update(question_words)

    # Extract named entities (capitalized multi-word phrases)
    named_entities = extract_named_entities(market.title + " " + market.question)
    protected.update(named_entities)

    # Convert to sorted list for consistent ordering
    return sorted(list(protected))


def extract_key_words(text: str) -> Set[str]:
    """
    Extract key words from text, filtering out common stopwords.

    Args:
        text: Text to extract key words from

    Returns:
        Set of key words (lowercased)
    """
    # Common stopwords to filter out
    stopwords = {
        'will', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
        'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
        'this', 'that', 'these', 'those', 'what', 'which', 'who',
        'when', 'where', 'why', 'how', 'if', 'their', 'there',
        'they', 'it', 'its', 'his', 'her', 'their'
    }

    # Extract words (keep numbers and letters)
    words = re.findall(r'\b\w+\b', text.lower())

    # Filter out stopwords and short words
    key_words = {
        word for word in words
        if word not in stopwords and len(word) > 2
    }

    return key_words


def extract_named_entities(text: str) -> Set[str]:
    """
    Extract named entities (capitalized phrases) from text.

    Simple heuristic: look for sequences of capitalized words.

    Args:
        text: Text to extract named entities from

    Returns:
        Set of named entities (lowercased)
    """
    # Find sequences of capitalized words
    # Pattern: capitalized word followed by optional capitalized words
    pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    matches = re.findall(pattern, text)

    # Convert to lowercase and filter out single common words
    entities = set()
    for match in matches:
        # Skip single-word matches that are likely not named entities
        if ' ' in match or len(match) > 4:
            entities.add(match.lower())

    return entities
