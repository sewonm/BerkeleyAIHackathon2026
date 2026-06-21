"""
Redis-Enhanced Advanced Compression Pipeline.

This is an enhanced version of AdvancedCompressor that uses Redis vector search for:
1. Semantic similarity-based claim clustering (vs token-based)
2. Source deduplication via vector similarity
3. Compression result caching
4. Source diversity measurement

For comparison/benchmarking against the baseline token-based compressor.
"""

from typing import List, Dict, Any, Optional
import math
import hashlib

from app.compression.schemas_advanced import (
    EnhancedEvidenceChunk,
    EnhancedCompressionRequest,
    AdvancedCompressionResult,
    ExtractedClaim,
    EvidenceGraph,
    ConsensusLedger,
    ConsensusItem,
    CompressionMetrics,
)
from app.compression.extractors import ClaudeClaimExtractor, HeuristicClaimExtractor
from app.compression.graph_builder import EvidenceGraphBuilder
from app.compression.information_value import InformationValueScorer
from app.compression.redis_similarity import RedisVectorSearch
from app.utils.token_counter import count_tokens


class RedisEnhancedConsensusClusterer:
    """
    Consensus clusterer that uses Redis vector similarity.

    Falls back to token-based similarity if Redis unavailable.
    """

    def __init__(self, similarity_threshold: float = 0.6, redis_search: Optional[RedisVectorSearch] = None):
        self.similarity_threshold = similarity_threshold
        self.redis_search = redis_search

    def cluster_claims(self, claims: List[ExtractedClaim], market_id: str) -> List[ConsensusItem]:
        """
        Cluster claims into consensus items using Redis vector similarity.

        Args:
            claims: List of extracted claims
            market_id: Market ID for Redis storage

        Returns:
            List of consensus items
        """
        if not claims:
            return []

        # Add all claims to Redis first
        if self.redis_search and self.redis_search.enabled:
            print("[RedisClusterer] Adding claims to Redis for vector search...")
            for claim in claims:
                self.redis_search.add_claim(claim, market_id)

        # Group claims by direction first
        yes_claims = [c for c in claims if c.direction == "YES"]
        no_claims = [c for c in claims if c.direction == "NO"]
        neutral_claims = [c for c in claims if c.direction == "NEUTRAL"]

        consensus_items = []

        # Cluster each direction separately
        consensus_items.extend(self._cluster_by_direction(yes_claims, "YES", market_id))
        consensus_items.extend(self._cluster_by_direction(no_claims, "NO", market_id))
        consensus_items.extend(self._cluster_by_direction(neutral_claims, "NEUTRAL", market_id))

        return consensus_items

    def _cluster_by_direction(
        self,
        claims: List[ExtractedClaim],
        direction: str,
        market_id: str
    ) -> List[ConsensusItem]:
        """Cluster claims of the same direction"""
        if not claims:
            return []

        clusters = []
        used_claim_ids = set()

        for i, claim in enumerate(claims):
            if claim.claim_id in used_claim_ids:
                continue

            # Start a new cluster
            cluster_claims = [claim]
            used_claim_ids.add(claim.claim_id)

            # Find similar claims using Redis or token-based similarity
            if self.redis_search and self.redis_search.enabled:
                # Use Redis vector similarity
                similar_claim_ids = self.redis_search.find_similar_claims(
                    claim,
                    market_id,
                    direction=direction,
                    top_k=len(claims),
                    similarity_threshold=self.similarity_threshold
                )

                for similar_id, similarity_score in similar_claim_ids:
                    if similar_id in used_claim_ids:
                        continue

                    # Find the claim object
                    for other_claim in claims:
                        if other_claim.claim_id == similar_id:
                            cluster_claims.append(other_claim)
                            used_claim_ids.add(similar_id)
                            break

            else:
                # Fallback to token-based similarity
                for j, other_claim in enumerate(claims):
                    if i == j or other_claim.claim_id in used_claim_ids:
                        continue

                    similarity = self._calculate_token_similarity(claim, other_claim)
                    if similarity >= self.similarity_threshold:
                        cluster_claims.append(other_claim)
                        used_claim_ids.add(other_claim.claim_id)

            # Create consensus item
            consensus = self._create_consensus_item(cluster_claims, direction)
            clusters.append(consensus)

        return clusters

    def _calculate_token_similarity(self, claim1: ExtractedClaim, claim2: ExtractedClaim) -> float:
        """Fallback token-based Jaccard similarity"""
        tokens1 = set(claim1.canonical_text.lower().split())
        tokens2 = set(claim2.canonical_text.lower().split())

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _create_consensus_item(
        self,
        claims: List[ExtractedClaim],
        direction: str
    ) -> ConsensusItem:
        """Create a consensus item from a cluster of claims"""
        # Use the highest-impact claim as canonical
        canonical_claim = max(claims, key=lambda c: c.market_impact_score)

        # Aggregate source info
        source_agents = list(set(c.source_agent for c in claims))
        source_diversity = len(source_agents) / max(len(claims), 1)

        # Calculate consensus entropy
        confidences = [c.confidence for c in claims]
        avg_confidence = sum(confidences) / len(confidences)
        variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
        entropy = math.sqrt(variance)

        # Determine agreement level
        if entropy < 0.1:
            agreement = "high"
        elif entropy < 0.3:
            agreement = "medium"
        else:
            agreement = "low"

        # Aggregate probability shifts
        prob_shifts = [c.estimated_probability_shift for c in claims]
        avg_prob_shift = sum(prob_shifts) / len(prob_shifts)

        # Collect all entities, dates, numbers
        all_entities = list(set(e for c in claims for e in c.entities))
        all_dates = list(set(d for c in claims for d in c.dates))
        all_numbers = list(set(n for c in claims for n in c.numbers))

        return ConsensusItem(
            canonical_claim=canonical_claim.claim_text,
            direction=direction,
            source_count=len(claims),
            source_agents=source_agents,
            source_diversity_score=source_diversity,
            agreement_level=agreement,
            consensus_entropy=entropy,
            confidence=avg_confidence,
            estimated_probability_shift=avg_prob_shift,
            information_value=0.0,  # Will be calculated later
            supporting_claim_ids=[c.claim_id for c in claims],
            entities=all_entities,
            dates=all_dates,
            numbers=all_numbers,
            metadata={
                "cluster_size": len(claims),
                "clustering_method": "redis_vector" if self.redis_search and self.redis_search.enabled else "token_jaccard"
            }
        )


class RedisEnhancedCompressor:
    """
    Redis-enhanced compression pipeline.

    Adds:
    - Vector-based claim clustering
    - Source deduplication
    - Result caching
    - Diversity measurement
    """

    def __init__(self, use_claude: bool = True, use_redis: bool = True):
        """
        Initialize the Redis-enhanced compressor.

        Args:
            use_claude: Whether to attempt Claude extraction
            use_redis: Whether to use Redis vector search
        """
        self.use_claude = use_claude
        self.use_redis = use_redis

        # Initialize components
        if use_claude:
            self.claim_extractor = ClaudeClaimExtractor()
        else:
            self.claim_extractor = HeuristicClaimExtractor()

        self.graph_builder = EvidenceGraphBuilder()

        # Initialize Redis
        self.redis_search = None
        if use_redis:
            self.redis_search = RedisVectorSearch(use_cache=True)
            if not self.redis_search.enabled:
                print("[RedisCompressor] Redis not available, falling back to token-based clustering")
                self.redis_search = None

        # Initialize clusterer with Redis
        self.consensus_clusterer = RedisEnhancedConsensusClusterer(
            similarity_threshold=0.6,
            redis_search=self.redis_search
        )

        self.value_scorer = InformationValueScorer()

        # Statistics
        self.stats = {
            "claude_calls": 0,
            "claude_failures": 0,
            "heuristic_fallbacks": 0,
            "redis_hits": 0,
            "redis_misses": 0,
        }

    def compress(self, request: EnhancedCompressionRequest) -> AdvancedCompressionResult:
        """
        Run the Redis-enhanced compression pipeline.

        Args:
            request: Compression request

        Returns:
            Compression result
        """
        print(f"[RedisCompressor] Starting compression for market {request.market_id}")
        print(f"[RedisCompressor] Redis enabled: {self.redis_search is not None}")

        # Check cache first
        if self.redis_search:
            cached_result = self._check_cache(request)
            if cached_result:
                self.stats["redis_hits"] += 1
                print("[RedisCompressor] Using cached result")
                return cached_result
            else:
                self.stats["redis_misses"] += 1

        # Measure source diversity BEFORE processing
        diversity_metrics = None
        if self.redis_search:
            print("[RedisCompressor] Measuring source diversity...")
            diversity_metrics = self.redis_search.measure_source_diversity(
                request.evidence_chunks,
                similarity_threshold=0.85
            )
            print(f"[RedisCompressor] Source diversity: {diversity_metrics['diversity_score']:.2f}")
            print(f"[RedisCompressor] Effective unique sources: {diversity_metrics['effective_unique_sources']}/{diversity_metrics['total_sources']}")

        # Step 1: Extract claims
        print("[RedisCompressor] Step 1: Extracting claims...")
        all_claims = self._extract_all_claims(
            chunks=request.evidence_chunks,
            market_question=request.market_question,
            resolution_criteria=request.resolution_criteria
        )
        print(f"[RedisCompressor] Extracted {len(all_claims)} claims")

        # Step 2: Build evidence graph
        print("[RedisCompressor] Step 2: Building evidence graph...")
        evidence_graph = self.graph_builder.build_graph(
            market_id=request.market_id,
            market_question=request.market_question,
            claims=all_claims
        )
        print(f"[RedisCompressor] Graph: {len(evidence_graph.nodes)} nodes, {len(evidence_graph.edges)} edges")

        # Step 3: Cluster into consensus items (using Redis)
        print("[RedisCompressor] Step 3: Clustering claims (Redis-enhanced)...")
        consensus_items = self.consensus_clusterer.cluster_claims(all_claims, request.market_id)
        print(f"[RedisCompressor] Created {len(consensus_items)} consensus items")

        # Step 4: Score by information value
        print("[RedisCompressor] Step 4: Scoring by information value...")
        consensus_items = self.value_scorer.score_items(
            consensus_items,
            current_yes_price=request.current_yes_price
        )

        # Step 5: Apply aggressiveness filter
        aggressiveness = request.aggressiveness or 0.5
        threshold = aggressiveness * 0.6
        consensus_items = [item for item in consensus_items if item.information_value >= threshold]
        print(f"[RedisCompressor] After aggressiveness filter ({aggressiveness:.2f}): {len(consensus_items)} items")

        consensus_ledger = ConsensusLedger(
            market_id=request.market_id,
            consensus_items=consensus_items
        )

        # Step 6: Identify contradictions and missing info
        contradictions = self._identify_contradictions(evidence_graph, consensus_items)
        missing_info = self._identify_missing_info(all_claims)

        # Step 7: Generate compressed context
        print("[RedisCompressor] Step 5: Generating compressed context...")
        compressed_context = self._generate_compressed_context(
            request=request,
            consensus_ledger=consensus_ledger,
            evidence_graph=evidence_graph,
            contradictions=contradictions,
            missing_info=missing_info,
            diversity_metrics=diversity_metrics
        )

        # Calculate metrics
        raw_text = " ".join([chunk.text for chunk in request.evidence_chunks])
        raw_tokens = count_tokens(raw_text)
        compressed_tokens = count_tokens(compressed_context)
        compression_ratio = raw_tokens / compressed_tokens if compressed_tokens > 0 else 0.0

        metrics = CompressionMetrics(
            raw_token_count=raw_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=round(compression_ratio, 2),
            token_budget=request.token_budget or 3000,
            total_claims_extracted=len(all_claims),
            total_consensus_items=len(consensus_items),
            yes_consensus_count=len(consensus_ledger.get_by_direction("YES")),
            no_consensus_count=len(consensus_ledger.get_by_direction("NO")),
            neutral_consensus_count=len(consensus_ledger.get_by_direction("NEUTRAL")),
            graph_node_count=len(evidence_graph.nodes),
            graph_edge_count=len(evidence_graph.edges),
            claude_calls=self.stats["claude_calls"],
            claude_failures=self.stats["claude_failures"],
            heuristic_fallbacks=self.stats["heuristic_fallbacks"],
            redis_hits=self.stats["redis_hits"],
            redis_misses=self.stats["redis_misses"],
        )

        print(f"[RedisCompressor] Compression complete: {compression_ratio:.2f}x")

        # Create result
        result = AdvancedCompressionResult(
            request_id=request.request_id,
            market_id=request.market_id,
            evidence_graph=evidence_graph,
            consensus_ledger=consensus_ledger,
            top_supporting_evidence=consensus_ledger.get_top_by_value(5, "YES"),
            top_opposing_evidence=consensus_ledger.get_top_by_value(5, "NO"),
            contradictions=contradictions,
            missing_info=missing_info,
            compressed_context=compressed_context,
            metrics=metrics,
            mode="graph-consensus-redis"
        )

        # Cache the result
        if self.redis_search:
            self._cache_result(request, result)

        return result

    def _check_cache(self, request: EnhancedCompressionRequest) -> Optional[AdvancedCompressionResult]:
        """Check if compression result is cached"""
        if not self.redis_search:
            return None

        # Hash the evidence
        evidence_text = "".join([chunk.text for chunk in request.evidence_chunks])
        evidence_hash = hashlib.md5(evidence_text.encode()).hexdigest()

        # Check cache
        cached = self.redis_search.get_cached_compression(
            request.market_id,
            evidence_hash
        )

        if cached:
            # Reconstruct result from cached dict
            return AdvancedCompressionResult(**cached)

        return None

    def _cache_result(self, request: EnhancedCompressionRequest, result: AdvancedCompressionResult):
        """Cache compression result"""
        if not self.redis_search:
            return

        # Hash the evidence
        evidence_text = "".join([chunk.text for chunk in request.evidence_chunks])
        evidence_hash = hashlib.md5(evidence_text.encode()).hexdigest()

        # Cache for 1 hour
        self.redis_search.cache_compression_result(
            request.market_id,
            evidence_hash,
            result.dict(),
            ttl=3600
        )

    def _extract_all_claims(
        self,
        chunks: List[EnhancedEvidenceChunk],
        market_question: str,
        resolution_criteria: str
    ) -> List[ExtractedClaim]:
        """Extract claims from all chunks"""
        all_claims = []

        for chunk in chunks:
            if isinstance(self.claim_extractor, ClaudeClaimExtractor):
                claims, method = self.claim_extractor.extract_claims(
                    chunk,
                    market_question,
                    resolution_criteria
                )

                if method == "claude":
                    self.stats["claude_calls"] += 1
                elif method == "heuristic_fallback":
                    self.stats["heuristic_fallbacks"] += 1
            else:
                claims = self.claim_extractor.extract_claims(
                    chunk,
                    market_question,
                    resolution_criteria
                )
                self.stats["heuristic_fallbacks"] += 1

            all_claims.extend(claims)

        return all_claims

    def _identify_contradictions(
        self,
        graph: EvidenceGraph,
        consensus_items: List[ConsensusItem]
    ) -> List[Dict[str, Any]]:
        """Identify contradictions from the evidence graph"""
        contradictions = []
        conflict_edges = [e for e in graph.edges if e.edge_type == "conflicts_with"]

        claim_to_consensus = {}
        for item in consensus_items:
            for claim_id in item.supporting_claim_ids:
                claim_to_consensus[claim_id] = item

        seen_pairs = set()
        for edge in conflict_edges:
            consensus1 = claim_to_consensus.get(edge.source_node_id)
            consensus2 = claim_to_consensus.get(edge.target_node_id)

            if consensus1 and consensus2:
                pair_key = tuple(sorted([consensus1.consensus_id, consensus2.consensus_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                contradictions.append({
                    "claim1": consensus1.canonical_claim[:100],
                    "claim2": consensus2.canonical_claim[:100],
                    "direction1": consensus1.direction,
                    "direction2": consensus2.direction,
                    "weight": edge.weight
                })

        return contradictions[:5]

    def _identify_missing_info(self, claims: List[ExtractedClaim]) -> List[str]:
        """Identify missing information from claims"""
        missing_info = []

        has_numbers = any(claim.numbers for claim in claims)
        has_dates = any(claim.dates for claim in claims)
        has_official = any("official" in claim.claim_text.lower() for claim in claims)

        if not has_numbers:
            missing_info.append("Quantitative data or metrics")
        if not has_dates:
            missing_info.append("Recent time-specific information")
        if not has_official:
            missing_info.append("Official announcements or confirmations")

        missing_info.extend([
            "Real-time market data",
            "Updated news from the last 24 hours"
        ])

        return missing_info[:5]

    def _generate_compressed_context(
        self,
        request: EnhancedCompressionRequest,
        consensus_ledger: ConsensusLedger,
        evidence_graph: EvidenceGraph,
        contradictions: List[Dict[str, Any]],
        missing_info: List[str],
        diversity_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate the final compressed context text"""
        lines = []

        lines.append("=" * 60)
        lines.append("COMPRESSED EVIDENCE CONTEXT (Redis-Enhanced)")
        lines.append("=" * 60)
        lines.append("")

        lines.append("MARKET:")
        lines.append(f"{request.market_question}")
        lines.append("")

        if request.current_yes_price is not None:
            lines.append("MARKET PRICE:")
            lines.append(f"YES = {request.current_yes_price:.2f}, NO = {request.current_no_price:.2f}")
            lines.append("")

        # Source diversity metrics
        if diversity_metrics:
            lines.append("SOURCE DIVERSITY:")
            lines.append(f"Total sources: {diversity_metrics['total_sources']}")
            lines.append(f"Effective unique: {diversity_metrics['effective_unique_sources']}")
            lines.append(f"Diversity score: {diversity_metrics['diversity_score']:.2f}")
            if diversity_metrics.get('duplicate_groups'):
                lines.append(f"Duplicate groups: {len(diversity_metrics['duplicate_groups'])}")
            lines.append("")

        lines.append("RESOLUTION CRITERIA:")
        lines.append(f"{request.resolution_criteria}")
        lines.append("")

        top_yes = consensus_ledger.get_top_by_value(5, "YES")
        if top_yes:
            lines.append("TOP YES EVIDENCE:")
            for i, item in enumerate(top_yes, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                method = item.metadata.get('clustering_method', 'unknown')
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f} | Method: {method}")
            lines.append("")

        top_no = consensus_ledger.get_top_by_value(5, "NO")
        if top_no:
            lines.append("TOP NO EVIDENCE:")
            for i, item in enumerate(top_no, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                method = item.metadata.get('clustering_method', 'unknown')
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f} | Method: {method}")
            lines.append("")

        if contradictions:
            lines.append("CONTRADICTIONS:")
            for i, contra in enumerate(contradictions, 1):
                lines.append(f"{i}. {contra['claim1']} [{contra['direction1']}]")
                lines.append(f"   vs. {contra['claim2']} [{contra['direction2']}]")
            lines.append("")

        if missing_info:
            lines.append("MISSING INFORMATION:")
            for info in missing_info:
                lines.append(f"- {info}")
            lines.append("")

        lines.append("GRAPH SUMMARY:")
        lines.append(f"- {len(evidence_graph.nodes)} nodes")
        lines.append(f"- {len(evidence_graph.edges)} edges")
        lines.append(f"- {len(consensus_ledger.consensus_items)} consensus clusters")
        lines.append("")

        return "\n".join(lines)
