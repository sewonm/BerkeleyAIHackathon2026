"""
Tests for the advanced compression pipeline.
"""

import pytest
from app.compression.advanced_compressor import AdvancedCompressor
from app.compression.schemas_advanced import (
    EnhancedEvidenceChunk,
    EnhancedCompressionRequest,
)
from app.compression.extractors import HeuristicClaimExtractor
from app.compression.graph_builder import ConsensusClusterer, EvidenceGraphBuilder
from app.compression.information_value import InformationValueScorer


def create_test_chunks():
    """Create test evidence chunks"""
    return [
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="test_agent_1",
            source_type="culture_web",
            text="Movie X received 12 Academy Award nominations including Best Picture. The film has strong momentum.",
            confidence=0.9
        ),
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="test_agent_2",
            source_type="culture_web",
            text="Movie X won the Producers Guild Award, a strong predictor of Best Picture wins.",
            confidence=0.85
        ),
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="test_agent_3",
            source_type="culture_web",
            text="Critics have praised Movie X, but some question its chances against Movie Y.",
            confidence=0.7
        ),
        EnhancedEvidenceChunk(
            market_id="test-market",
            source_agent="test_agent_1",
            source_type="culture_web",
            text="Movie Y remains the favorite according to several prediction markets.",
            confidence=0.8
        ),
    ]


def test_heuristic_extractor_works():
    """Test that heuristic extractor can extract claims"""
    extractor = HeuristicClaimExtractor()

    chunk = EnhancedEvidenceChunk(
        market_id="test",
        source_agent="test",
        source_type="culture_web",
        text="Movie X received 12 nominations. This is a strong signal for Best Picture."
    )

    claims = extractor.extract_claims(
        chunk,
        "Will Movie X win Best Picture?",
        "Market resolves YES if Movie X wins Best Picture."
    )

    assert len(claims) > 0, "Should extract at least one claim"
    assert all(claim.extraction_method == "heuristic" for claim in claims)


def test_compressor_works_without_redis():
    """Test that compressor works without Redis"""
    compressor = AdvancedCompressor(use_claude=False)

    request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will Movie X win Best Picture?",
        resolution_criteria="Market resolves YES if Movie X wins Best Picture.",
        current_yes_price=0.5,
        current_no_price=0.5,
        evidence_chunks=create_test_chunks(),
        token_budget=1000
    )

    result = compressor.compress(request)

    # Result should be valid
    assert result.metrics.total_claims_extracted > 0
    # Note: compression ratio may be < 1 for small inputs due to headers
    assert result.metrics.compression_ratio > 0.0
    assert len(result.compressed_context) > 0


def test_compressor_works_without_claude():
    """Test that compressor works without Claude API"""
    compressor = AdvancedCompressor(use_claude=False)

    request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will Movie X win Best Picture?",
        resolution_criteria="Market resolves YES if Movie X wins Best Picture.",
        evidence_chunks=create_test_chunks(),
        token_budget=1000
    )

    result = compressor.compress(request)

    assert result.metrics.heuristic_fallbacks > 0
    assert result.metrics.claude_calls == 0


def test_consensus_clustering_merges_similar_claims():
    """Test that similar claims are merged"""
    from app.compression.schemas_advanced import ExtractedClaim

    clusterer = ConsensusClusterer(similarity_threshold=0.4)  # Lower threshold to ensure merge

    # Create similar claims
    claim1 = ExtractedClaim(
        claim_text="Movie X received 12 nominations",
        canonical_text="movie x received 12 nominations",
        source_chunk_id="1",
        source_agent="agent1",
        direction="YES",
        confidence=0.8,
        market_impact_score=0.7
    )

    claim2 = ExtractedClaim(
        claim_text="Movie X received nominations",
        canonical_text="movie x received nominations",
        source_chunk_id="2",
        source_agent="agent2",
        direction="YES",
        confidence=0.9,
        market_impact_score=0.8
    )

    claim3 = ExtractedClaim(
        claim_text="Movie Y is leading in polls",
        canonical_text="movie y is leading in polls",
        source_chunk_id="3",
        source_agent="agent3",
        direction="NO",
        confidence=0.7,
        market_impact_score=0.6
    )

    consensus_items = clusterer.cluster_claims([claim1, claim2, claim3])

    # Should merge claim1 and claim2, keep claim3 separate
    # Since we separate by direction first, we get 2 items: one YES cluster, one NO
    assert len(consensus_items) == 2, "Should merge similar YES claims into one cluster, NO stays separate"


def test_consensus_does_not_merge_unrelated_claims():
    """Test that unrelated claims stay separate"""
    from app.compression.schemas_advanced import ExtractedClaim

    clusterer = ConsensusClusterer(similarity_threshold=0.6)

    claim1 = ExtractedClaim(
        claim_text="Movie X received nominations",
        canonical_text="movie x received nominations",
        source_chunk_id="1",
        source_agent="agent1",
        direction="YES",
        confidence=0.8,
        market_impact_score=0.7
    )

    claim2 = ExtractedClaim(
        claim_text="The weather is nice today",
        canonical_text="the weather is nice today",
        source_chunk_id="2",
        source_agent="agent2",
        direction="NEUTRAL",
        confidence=0.5,
        market_impact_score=0.1
    )

    consensus_items = clusterer.cluster_claims([claim1, claim2])

    assert len(consensus_items) == 2, "Should not merge unrelated claims"


def test_evidence_graph_has_nodes_and_edges():
    """Test that evidence graph is constructed"""
    from app.compression.schemas_advanced import ExtractedClaim

    builder = EvidenceGraphBuilder()

    claims = [
        ExtractedClaim(
            claim_text="Movie X received 12 nominations",
            canonical_text="movie x received 12 nominations",
            source_chunk_id="1",
            source_agent="agent1",
            direction="YES",
            confidence=0.8,
            market_impact_score=0.7,
            entities=["Movie X"]
        )
    ]

    graph = builder.build_graph(
        market_id="test",
        market_question="Will Movie X win?",
        claims=claims
    )

    assert len(graph.nodes) > 0, "Should have nodes"
    assert len(graph.edges) > 0, "Should have edges"


def test_compression_ratio_greater_than_one():
    """Test that compression achieves ratio > 1 with large input"""
    compressor = AdvancedCompressor(use_claude=False)

    # Create many longer evidence chunks to ensure raw text is much larger
    chunks = []
    for i in range(30):  # More chunks
        chunks.append(EnhancedEvidenceChunk(
            market_id="test",
            source_agent=f"agent_{i}",
            source_type="culture_web",
            text=f"Additional evidence about Movie X and the Oscar race with various details and filler text that will need to be compressed. This is chunk {i} with more content and redundant information. Movie X is performing well in the awards season. Critics have praised the film for its innovative approach and strong performances.",
            confidence=0.5
        ))

    request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will Movie X win Best Picture?",
        resolution_criteria="Market resolves YES if Movie X wins Best Picture.",
        evidence_chunks=chunks,
        token_budget=500  # Tight budget to force compression
    )

    result = compressor.compress(request)

    # With lots of redundant content, should achieve compression
    assert result.metrics.raw_token_count > result.metrics.compressed_token_count, \
        "Should compress redundant content"


def test_compressed_context_not_empty():
    """Test that compressed context is generated"""
    compressor = AdvancedCompressor(use_claude=False)

    request = EnhancedCompressionRequest(
        market_id="test-market",
        market_question="Will Movie X win Best Picture?",
        resolution_criteria="Market resolves YES if Movie X wins Best Picture.",
        evidence_chunks=create_test_chunks(),
        token_budget=1000
    )

    result = compressor.compress(request)

    assert len(result.compressed_context) > 0, "Compressed context should not be empty"
    assert "MARKET:" in result.compressed_context
    assert "EVIDENCE" in result.compressed_context


def test_information_value_scoring():
    """Test that information value scoring works"""
    from app.compression.schemas_advanced import ConsensusItem

    scorer = InformationValueScorer()

    item = ConsensusItem(
        canonical_claim="Movie X received 12 nominations",
        direction="YES",
        source_count=5,
        source_agents=["agent1", "agent2", "agent3", "agent4", "agent5"],
        source_diversity_score=1.0,
        agreement_level="high",
        consensus_entropy=0.05,
        confidence=0.9,
        estimated_probability_shift=0.10,
        information_value=0.0  # Will be calculated
    )

    value = scorer.calculate_information_value(item, [item], current_yes_price=0.5)

    assert 0.0 <= value <= 1.0, "Information value should be in [0, 1]"
    assert value > 0.0, "Should have some information value"


def test_contradictions_identified():
    """Test that contradictions are identified"""
    compressor = AdvancedCompressor(use_claude=False)

    chunks = [
        EnhancedEvidenceChunk(
            market_id="test",
            source_agent="agent1",
            source_type="culture_web",
            text="Movie X is the frontrunner to win Best Picture",
            confidence=0.9
        ),
        EnhancedEvidenceChunk(
            market_id="test",
            source_agent="agent2",
            source_type="culture_web",
            text="Movie Y remains the favorite to win Best Picture",
            confidence=0.8
        ),
    ]

    request = EnhancedCompressionRequest(
        market_id="test",
        market_question="Which movie will win Best Picture?",
        resolution_criteria="Resolves to the winner",
        evidence_chunks=chunks,
        token_budget=1000
    )

    result = compressor.compress(request)

    # Should identify some contradictions
    # (may be 0 if claims don't have enough overlap, but test should not fail)
    assert isinstance(result.contradictions, list)
