"""
Information-value scoring for consensus items.

This implements an information-theoretic inspired scoring system
to rank evidence by approximate decision value.
"""

import math
from typing import List, Optional
from datetime import datetime

from app.compression.schemas_advanced import ConsensusItem


class InformationValueScorer:
    """
    Scores consensus items by approximate information value.

    Formula:
    information_value =
        0.30 * probability_shift_score
      + 0.20 * source_consensus_score
      + 0.15 * source_diversity_score
      + 0.15 * recency_score
      + 0.10 * contradiction_importance
      + 0.10 * source_reliability
      - 0.20 * redundancy_score
      - 0.15 * priced_in_score
    """

    def __init__(self):
        pass

    def score_items(
        self,
        items: List[ConsensusItem],
        current_yes_price: Optional[float] = None
    ) -> List[ConsensusItem]:
        """
        Score all consensus items.

        Args:
            items: List of consensus items
            current_yes_price: Current market YES price

        Returns:
            Items with information_value updated
        """
        for item in items:
            item.information_value = self.calculate_information_value(
                item,
                items,
                current_yes_price
            )

        return items

    def calculate_information_value(
        self,
        item: ConsensusItem,
        all_items: List[ConsensusItem],
        current_yes_price: Optional[float] = None
    ) -> float:
        """
        Calculate information value for a single item.

        Args:
            item: Consensus item to score
            all_items: All consensus items (for redundancy calc)
            current_yes_price: Current market YES price

        Returns:
            Information value score (0-1)
        """
        # Component scores
        prob_shift_score = self._probability_shift_score(item)
        consensus_score = self._source_consensus_score(item)
        diversity_score = item.source_diversity_score
        recency_score = self._recency_score(item)
        contradiction_score = self._contradiction_importance(item)
        reliability_score = self._source_reliability(item)
        redundancy_score = self._redundancy_score(item, all_items)
        priced_in_score = self._priced_in_score(item, current_yes_price)

        # Weighted sum
        value = (
            0.30 * prob_shift_score +
            0.20 * consensus_score +
            0.15 * diversity_score +
            0.15 * recency_score +
            0.10 * contradiction_score +
            0.10 * reliability_score -
            0.20 * redundancy_score -
            0.15 * priced_in_score
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, value))

    def _probability_shift_score(self, item: ConsensusItem) -> float:
        """
        Score based on estimated probability shift.

        Larger shifts = more valuable
        """
        # Normalize shift (usually -0.15 to 0.15) to 0-1
        abs_shift = abs(item.estimated_probability_shift)
        return min(abs_shift / 0.15, 1.0)

    def _source_consensus_score(self, item: ConsensusItem) -> float:
        """
        Score based on consensus strength.

        Low entropy (high agreement) = higher score
        """
        # Entropy is 0-1 (approximately), invert it
        return 1.0 - item.consensus_entropy

    def _recency_score(self, item: ConsensusItem) -> float:
        """
        Score based on recency.

        For MVP, we don't have timestamps, so use a default.
        """
        # TODO: Implement actual recency scoring when timestamps are available
        return 0.7  # Default moderate recency

    def _contradiction_importance(self, item: ConsensusItem) -> float:
        """
        Score based on contradictions.

        Items that contradict others are more important to surface.
        """
        # If has opposing claims, boost importance
        if item.opposing_claim_ids:
            return 0.8
        return 0.3

    def _source_reliability(self, item: ConsensusItem) -> float:
        """
        Score based on source reliability.

        For MVP, assume all sources are moderately reliable.
        """
        # More sources = more reliable
        if item.source_count >= 5:
            return 0.9
        elif item.source_count >= 3:
            return 0.7
        elif item.source_count >= 2:
            return 0.5
        else:
            return 0.3

    def _redundancy_score(self, item: ConsensusItem, all_items: List[ConsensusItem]) -> float:
        """
        Score based on redundancy with other items.

        High redundancy = penalty
        """
        # Simple heuristic: check for shared entities/keywords
        item_words = set(item.canonical_claim.lower().split())

        redundancy = 0.0
        for other in all_items:
            if other.consensus_id == item.consensus_id:
                continue

            other_words = set(other.canonical_claim.lower().split())
            overlap = item_words & other_words

            if overlap:
                redundancy += len(overlap) / max(len(item_words), len(other_words))

        # Normalize by number of other items
        if len(all_items) > 1:
            redundancy /= (len(all_items) - 1)

        return min(redundancy, 1.0)

    def _priced_in_score(self, item: ConsensusItem, current_yes_price: Optional[float]) -> float:
        """
        Score based on how much might already be priced in.

        If market price already reflects the claim's direction, it's less valuable.
        """
        if current_yes_price is None:
            return 0.5  # Unknown

        # If claim says YES but price is already high, it's priced in
        if item.direction == "YES" and current_yes_price > 0.6:
            return 0.7
        elif item.direction == "NO" and current_yes_price < 0.4:
            return 0.7
        else:
            return 0.3  # Not fully priced in
