"""Tests for the compression pipeline"""

import pytest
from app.schemas.market import Market
from app.schemas.evidence import EvidenceChunk
from app.compression.compressor import Compressor


def create_test_market():
    """Create a test market for testing"""
    return Market(
        market_id="test-market-1",
        title="Will Movie X win Best Picture?",
        question="Will Movie X win the Academy Award for Best Picture?",
        category="culture",
        current_yes_price=0.50,
        current_no_price=0.50,
        resolution_criteria="Market resolves YES if Movie X wins Best Picture.",
        protected_terms=["Movie X", "Best Picture", "Academy Award"]
    )


def create_test_evidence():
    """Create test evidence chunks"""
    return [
        EvidenceChunk(
            source_type="culture_web",
            text="Movie X received 12 Academy Award nominations including Best Picture.",
            confidence=0.9
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Critics praised Movie X as a masterpiece and predicted it would win Best Picture.",
            confidence=0.85
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="The weather was nice during the film festival.",
            confidence=0.5
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Various celebrities attended unrelated events this week.",
            confidence=0.4
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Movie X won the Producers Guild Award, a strong predictor of Best Picture.",
            confidence=0.95
        )
    ]


def test_compressor_reduces_token_count():
    """Test that compression actually compresses when budget is tight"""
    compressor = Compressor()
    market = create_test_market()

    # Create more evidence to ensure compression happens
    evidence = create_test_evidence()
    # Add more chunks to make raw context larger
    for i in range(10):
        evidence.append(EvidenceChunk(
            source_type="culture_web",
            text=f"Additional unique filler content about topic {i} that should be dropped due to low relevance when budget is tight. This content number {i} is different from other content.",
            confidence=0.3
        ))

    # Use a very tight budget to force dropping chunks
    result = compressor.compress(market, evidence, token_budget=100)

    # With a tight budget, we should either drop chunks or achieve compression
    # The raw token count should be larger than compressed (or we should have dropped chunks)
    has_compression = result.raw_token_count > result.compressed_token_count
    has_dropped_chunks = len(result.dropped_chunks) > 0

    assert has_compression or has_dropped_chunks, \
        f"Should achieve compression or drop chunks with tight budget (raw: {result.raw_token_count}, compressed: {result.compressed_token_count}, dropped: {len(result.dropped_chunks)})"


def test_compressor_respects_token_budget():
    """Test that compressor respects the token budget"""
    compressor = Compressor()
    market = create_test_market()
    evidence = create_test_evidence()

    token_budget = 300
    result = compressor.compress(market, evidence, token_budget=token_budget)

    # Allow some margin for header text
    assert result.compressed_token_count <= token_budget + 100, \
        f"Compressed tokens ({result.compressed_token_count}) should be close to budget ({token_budget})"


def test_compressor_protected_terms():
    """Test that protected terms are extracted and included"""
    compressor = Compressor()
    market = create_test_market()
    evidence = create_test_evidence()

    result = compressor.compress(market, evidence, token_budget=1000)

    # Check that protected terms were extracted
    assert len(result.protected_terms) > 0, "Should extract protected terms"

    # Check that explicit protected terms are included
    protected_lower = [term.lower() for term in result.protected_terms]
    assert "movie x" in protected_lower or "best picture" in protected_lower, \
        "Should include explicit protected terms from market"


def test_compressor_keeps_high_score_chunks():
    """Test that high-scoring chunks are kept over low-scoring ones"""
    compressor = Compressor()
    market = create_test_market()

    # Create evidence with more chunks to ensure some are dropped
    evidence = create_test_evidence()
    for i in range(10):
        evidence.append(EvidenceChunk(
            source_type="culture_web",
            text=f"Low relevance filler text number {i} with no useful information about the market.",
            confidence=0.2
        ))

    # Use a tight budget to force dropping chunks
    result = compressor.compress(market, evidence, token_budget=150)

    # Check that we have some kept and some dropped chunks
    assert len(result.kept_chunks) > 0, "Should keep some chunks"
    assert len(result.dropped_chunks) > 0, "Should drop some chunks"

    # Verify that kept chunks have higher scores than dropped chunks
    if result.kept_chunks and result.dropped_chunks:
        min_kept_score = min(chunk['score'] for chunk in result.kept_chunks)
        max_dropped_score = max(chunk['score'] for chunk in result.dropped_chunks)

        # Generally, the lowest kept score should be >= highest dropped score
        # (with some tolerance for edge cases)
        assert min_kept_score >= max_dropped_score - 0.1, \
            f"Kept chunks should generally score higher than dropped chunks " \
            f"(min kept: {min_kept_score}, max dropped: {max_dropped_score})"


def test_compressor_calculates_compression_ratio():
    """Test that compression ratio is calculated correctly"""
    compressor = Compressor()
    market = create_test_market()
    evidence = create_test_evidence()

    result = compressor.compress(market, evidence, token_budget=500)

    expected_ratio = result.raw_token_count / result.compressed_token_count if result.compressed_token_count > 0 else 0

    assert abs(result.compression_ratio - expected_ratio) < 0.01, \
        f"Compression ratio should be correct (expected: {expected_ratio}, got: {result.compression_ratio})"


def test_compressor_empty_evidence():
    """Test compressor with empty evidence list"""
    compressor = Compressor()
    market = create_test_market()
    evidence = []

    result = compressor.compress(market, evidence, token_budget=1000)

    assert result.raw_token_count == 0, "Raw token count should be 0 for empty evidence"
    assert result.compressed_token_count == 0, "Compressed token count should be 0 for empty evidence"
    assert result.compression_ratio == 0.0, "Compression ratio should be 0 for empty evidence"
    assert len(result.kept_chunks) == 0, "Should have no kept chunks"
    assert len(result.dropped_chunks) == 0, "Should have no dropped chunks"


def test_compressor_deduplication():
    """Test that near-duplicate chunks are deduplicated"""
    compressor = Compressor()
    market = create_test_market()

    # Create evidence with near-duplicates
    evidence = [
        EvidenceChunk(
            source_type="culture_web",
            text="Movie X received 12 Academy Award nominations.",
            confidence=0.9
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Movie X received 12 Academy Award nominations.",  # Exact duplicate
            confidence=0.85
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Movie X got 12 Academy Award nominations.",  # Near duplicate
            confidence=0.8
        ),
        EvidenceChunk(
            source_type="culture_web",
            text="Something completely different about other topics.",
            confidence=0.7
        )
    ]

    result = compressor.compress(market, evidence, token_budget=1000)

    # The first three chunks are very similar, so some should be deduplicated
    # We should have fewer kept chunks than input chunks
    total_unique = len(result.kept_chunks) + len(result.dropped_chunks)
    assert total_unique < len(evidence), \
        f"Should deduplicate near-identical chunks (input: {len(evidence)}, unique: {total_unique})"


def test_compressor_compressed_context_format():
    """Test that compressed context has proper format"""
    compressor = Compressor()
    market = create_test_market()
    evidence = create_test_evidence()

    result = compressor.compress(market, evidence, token_budget=1000)

    # Check that compressed context includes market information
    assert market.title in result.compressed_context or "Market:" in result.compressed_context, \
        "Compressed context should include market information"

    # Check that it's not empty
    assert len(result.compressed_context) > 0, "Compressed context should not be empty"

    # Check that it includes some evidence
    assert "Evidence:" in result.compressed_context or any(
        chunk['text'][:20] in result.compressed_context for chunk in result.kept_chunks[:3]
    ), "Compressed context should include evidence text"
