"""
Advanced compression pipeline with graph-consensus compression.

This is the main compression logic that orchestrates:
- Claim extraction
- Graph building
- Consensus clustering
- Information-value scoring
- Compressed context generation
"""

from typing import List, Dict, Any, Optional
import math

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
from app.compression.graph_builder import EvidenceGraphBuilder, ConsensusClusterer
from app.compression.information_value import InformationValueScorer
from app.utils.token_counter import count_tokens


class AdvancedCompressor:
    """
    Main compression pipeline.

    Flow:
    1. Extract claims from evidence chunks
    2. Build evidence graph
    3. Cluster claims into consensus items
    4. Score consensus items by information value
    5. Generate compressed context
    """

    def __init__(self, use_claude: bool = True):
        """
        Initialize the compressor.

        Args:
            use_claude: Whether to attempt Claude extraction
        """
        self.use_claude = use_claude

        # Initialize components
        if use_claude:
            self.claim_extractor = ClaudeClaimExtractor()
        else:
            self.claim_extractor = HeuristicClaimExtractor()

        self.graph_builder = EvidenceGraphBuilder()
        self.consensus_clusterer = ConsensusClusterer(similarity_threshold=0.6)
        self.value_scorer = InformationValueScorer()

        # Statistics
        self.stats = {
            "claude_calls": 0,
            "claude_failures": 0,
            "heuristic_fallbacks": 0,
        }

    def compress(self, request: EnhancedCompressionRequest) -> AdvancedCompressionResult:
        """
        Run the full compression pipeline.

        Args:
            request: Compression request

        Returns:
            Compression result
        """
        print(f"[AdvancedCompressor] Starting compression for market {request.market_id}")
        print(f"[AdvancedCompressor] Evidence chunks: {len(request.evidence_chunks)}")

        # Step 1: Extract claims
        print("[AdvancedCompressor] Step 1: Extracting claims...")
        all_claims = self._extract_all_claims(
            chunks=request.evidence_chunks,
            market_question=request.market_question,
            resolution_criteria=request.resolution_criteria
        )
        print(f"[AdvancedCompressor] Extracted {len(all_claims)} claims")

        # Step 2: Build evidence graph
        print("[AdvancedCompressor] Step 2: Building evidence graph...")
        evidence_graph = self.graph_builder.build_graph(
            market_id=request.market_id,
            market_question=request.market_question,
            claims=all_claims
        )
        print(f"[AdvancedCompressor] Graph: {len(evidence_graph.nodes)} nodes, {len(evidence_graph.edges)} edges")

        # Step 3: Cluster into consensus items
        print("[AdvancedCompressor] Step 3: Clustering claims into consensus...")
        consensus_items = self.consensus_clusterer.cluster_claims(all_claims)
        print(f"[AdvancedCompressor] Created {len(consensus_items)} consensus items")

        # Step 4: Score by information value
        print("[AdvancedCompressor] Step 4: Scoring by information value...")
        consensus_items = self.value_scorer.score_items(
            consensus_items,
            current_yes_price=request.current_yes_price
        )

        # Create consensus ledger
        consensus_ledger = ConsensusLedger(
            market_id=request.market_id,
            consensus_items=consensus_items
        )

        # Step 5: Identify contradictions and missing info
        contradictions = self._identify_contradictions(evidence_graph, consensus_items)
        missing_info = self._identify_missing_info(all_claims)

        # Step 6: Generate compressed context
        print("[AdvancedCompressor] Step 5: Generating compressed context...")
        compressed_context = self._generate_compressed_context(
            request=request,
            consensus_ledger=consensus_ledger,
            evidence_graph=evidence_graph,
            contradictions=contradictions,
            missing_info=missing_info
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
        )

        print(f"[AdvancedCompressor] Compression complete:")
        print(f"  Raw tokens: {raw_tokens}")
        print(f"  Compressed tokens: {compressed_tokens}")
        print(f"  Ratio: {compression_ratio:.2f}x")

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
            mode=request.mode or "graph-consensus"
        )

        return result

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

        # Find conflict edges in the graph
        conflict_edges = [e for e in graph.edges if e.edge_type == "conflicts_with"]

        # Map claim IDs to consensus items
        claim_to_consensus = {}
        for item in consensus_items:
            for claim_id in item.supporting_claim_ids:
                claim_to_consensus[claim_id] = item

        # Create contradiction summaries
        seen_pairs = set()
        for edge in conflict_edges:
            # Get consensus items for both claims
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

        return contradictions[:5]  # Top 5 contradictions

    def _identify_missing_info(self, claims: List[ExtractedClaim]) -> List[str]:
        """Identify missing information from claims"""
        missing_info = []

        # Common missing info based on what's NOT in the claims
        has_numbers = any(claim.numbers for claim in claims)
        has_dates = any(claim.dates for claim in claims)
        has_official = any("official" in claim.claim_text.lower() for claim in claims)

        if not has_numbers:
            missing_info.append("Quantitative data or metrics")

        if not has_dates:
            missing_info.append("Recent time-specific information")

        if not has_official:
            missing_info.append("Official announcements or confirmations")

        # Add generic missing info
        missing_info.extend([
            "Real-time market data",
            "Updated news from the last 24 hours",
            "Expert analysis or commentary"
        ])

        return missing_info[:5]

    def _generate_compressed_context(
        self,
        request: EnhancedCompressionRequest,
        consensus_ledger: ConsensusLedger,
        evidence_graph: EvidenceGraph,
        contradictions: List[Dict[str, Any]],
        missing_info: List[str]
    ) -> str:
        """Generate the final compressed context text"""
        lines = []

        # Header
        lines.append("="* 60)
        lines.append("COMPRESSED EVIDENCE CONTEXT")
        lines.append("="* 60)
        lines.append("")

        # Market info
        lines.append("MARKET:")
        lines.append(f"{request.market_question}")
        lines.append("")

        if request.current_yes_price is not None:
            lines.append("MARKET PRICE:")
            lines.append(f"YES = {request.current_yes_price:.2f}, NO = {request.current_no_price:.2f}")
            lines.append("")

        # Resolution criteria
        lines.append("RESOLUTION CRITERIA:")
        lines.append(f"{request.resolution_criteria}")
        lines.append("")

        # Top YES evidence
        top_yes = consensus_ledger.get_top_by_value(5, "YES")
        if top_yes:
            lines.append("TOP YES EVIDENCE:")
            for i, item in enumerate(top_yes, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f}")
            lines.append("")

        # Top NO evidence
        top_no = consensus_ledger.get_top_by_value(5, "NO")
        if top_no:
            lines.append("TOP NO EVIDENCE:")
            for i, item in enumerate(top_no, 1):
                lines.append(f"{i}. {item.canonical_claim}")
                lines.append(f"   Sources: {item.source_count} | Agreement: {item.agreement_level} | Value: {item.information_value:.2f}")
            lines.append("")

        # Contradictions
        if contradictions:
            lines.append("CONTRADICTIONS:")
            for i, contra in enumerate(contradictions, 1):
                lines.append(f"{i}. {contra['claim1']} [{contra['direction1']}]")
                lines.append(f"   vs. {contra['claim2']} [{contra['direction2']}]")
            lines.append("")

        # Missing info
        if missing_info:
            lines.append("MISSING INFORMATION:")
            for info in missing_info:
                lines.append(f"- {info}")
            lines.append("")

        # Graph summary
        lines.append("GRAPH SUMMARY:")
        lines.append(f"- {len(evidence_graph.nodes)} nodes ({len([n for n in evidence_graph.nodes if n.node_type == 'claim'])} claims)")
        lines.append(f"- {len(evidence_graph.edges)} edges")
        lines.append(f"- {len(consensus_ledger.consensus_items)} consensus clusters")
        lines.append("")

        return "\n".join(lines)
