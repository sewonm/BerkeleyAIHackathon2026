"""Tests for the chunk scorer"""

import pytest
from app.compression.scorer import ChunkScorer


def test_scorer_relevant_chunks_score_higher():
    """Test that relevant chunks score higher than filler chunks"""
    protected_terms = ["Movie X", "Best Picture", "Academy Awards"]
    scorer = ChunkScorer(protected_terms)

    market_question = "Will Movie X win Best Picture at the Academy Awards?"

    # Relevant chunk with protected terms
    relevant_chunk = "Movie X received 12 Academy Award nominations including Best Picture."

    # Filler chunk with no protected terms
    filler_chunk = "The weather was nice today. Meanwhile, in other news, various people attended events."

    relevant_score = scorer.score(relevant_chunk, market_question)
    filler_score = scorer.score(filler_chunk, market_question)

    assert relevant_score > filler_score, \
        f"Relevant chunk should score higher (relevant: {relevant_score}, filler: {filler_score})"


def test_scorer_protected_terms_boost():
    """Test that chunks with protected terms score higher"""
    protected_terms = ["Stellar Dreams", "Oscar", "nomination"]
    scorer = ChunkScorer(protected_terms)

    market_question = "Will Stellar Dreams win an Oscar?"

    # Chunk with multiple protected terms
    with_protected = "Stellar Dreams received an Oscar nomination for Best Picture."

    # Similar chunk without protected terms
    without_protected = "The film received recognition from various organizations."

    with_score = scorer.score(with_protected, market_question)
    without_score = scorer.score(without_protected, market_question)

    assert with_score > without_score, \
        f"Chunk with protected terms should score higher (with: {with_score}, without: {without_score})"


def test_scorer_numbers_and_dates_boost():
    """Test that chunks with numbers and dates score higher"""
    protected_terms = []
    scorer = ChunkScorer(protected_terms)

    market_question = "Will the event happen?"

    # Chunk with numbers and dates
    with_data = "The event is scheduled for January 2027 with over 500 attendees expected."

    # Similar chunk without numbers or dates
    without_data = "The event is scheduled and many attendees are expected."

    with_score = scorer.score(with_data, market_question)
    without_score = scorer.score(without_data, market_question)

    assert with_score > without_score, \
        f"Chunk with numbers/dates should score higher (with: {with_score}, without: {without_score})"


def test_scorer_culture_signals():
    """Test that culture signal words boost scores"""
    protected_terms = []
    scorer = ChunkScorer(protected_terms)

    market_question = "Will the movie be successful?"

    # Chunk with culture signals
    with_signals = "The movie topped the box office with record-breaking streaming numbers and award nominations."

    # Chunk without culture signals
    without_signals = "The movie was shown in theaters and people watched it."

    with_score = scorer.score(with_signals, market_question)
    without_score = scorer.score(without_signals, market_question)

    assert with_score > without_score, \
        f"Chunk with culture signals should score higher (with: {with_score}, without: {without_score})"


def test_scorer_filler_penalty():
    """Test that filler words reduce scores"""
    protected_terms = []
    scorer = ChunkScorer(protected_terms)

    market_question = "What will happen?"

    # Chunk with lots of filler
    with_filler = "Meanwhile, however, in other news, furthermore, various unrelated things happened separately."

    # Chunk without filler
    without_filler = "The nomination was announced officially yesterday by the committee."

    with_score = scorer.score(with_filler, market_question)
    without_score = scorer.score(without_filler, market_question)

    assert without_score > with_score, \
        f"Chunk without filler should score higher (without: {without_score}, with: {with_score})"


def test_scorer_score_range():
    """Test that scores are in the valid range [0, 1]"""
    protected_terms = ["test", "example"]
    scorer = ChunkScorer(protected_terms)

    market_question = "Is this a test?"

    test_chunks = [
        "This is a test example with many test terms and example words.",
        "Completely unrelated content about something else entirely.",
        "Short text",
        "A" * 500,  # Very long text
        ""
    ]

    for chunk in test_chunks:
        score = scorer.score(chunk, market_question)
        assert 0.0 <= score <= 1.0, \
            f"Score {score} is out of valid range [0, 1] for chunk: {chunk[:50]}..."


def test_scorer_batch_scoring():
    """Test batch scoring functionality"""
    protected_terms = ["movie", "award"]
    scorer = ChunkScorer(protected_terms)

    market_question = "Will the movie win an award?"

    chunks = [
        "The movie won multiple awards at the ceremony.",
        "Weather forecast for tomorrow.",
        "The movie received critical acclaim."
    ]

    scores = scorer.score_batch(chunks, market_question)

    assert len(scores) == len(chunks), "Should return one score per chunk"
    assert all(0.0 <= score <= 1.0 for score in scores), "All scores should be in valid range"
    assert scores[0] > scores[1], "First chunk should score higher than weather chunk"
