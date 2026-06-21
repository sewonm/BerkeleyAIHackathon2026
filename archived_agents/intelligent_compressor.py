"""
Intelligent Compression Engine
Parses rough noisy text (JSON/HTML/scraped) and extracts clean facts
Builds market-centric graph with facts pointing to market question
"""

import json
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup


@dataclass
class ExtractedFact:
    """A clean fact extracted from noisy text"""
    text: str  # Clean fact statement
    confidence: float  # 0.0-1.0
    source_type: str  # sports_video, financial_research, etc.
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = None

    # Market relationship
    relation_to_market: str = "neutral"  # supports, contradicts, neutral
    relation_strength: float = 0.5

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MarketNode:
    """Central market question node"""
    question: str
    protected_terms: List[str]
    category: str = "unknown"


@dataclass
class CompressedGraph:
    """Market-centric fact graph"""
    market: MarketNode
    facts: List[ExtractedFact]
    supporting_facts: List[ExtractedFact]
    contradicting_facts: List[ExtractedFact]
    neutral_facts: List[ExtractedFact]

    def to_text(self, budget: int = 200) -> str:
        """Convert to ultra-compact text format"""
        lines = []
        tokens = 0

        # Market line
        market_line = f"Q: {self.market.question[:80]}"
        tokens += len(market_line.split())
        lines.append(market_line)

        # YES facts
        if self.supporting_facts:
            yes_parts = []
            for fact in sorted(self.supporting_facts, key=lambda f: f.confidence, reverse=True):
                part = f"{fact.text[:50]}({fact.confidence:.2f})"
                part_tokens = len(part.split())
                if tokens + part_tokens <= budget:
                    yes_parts.append(part)
                    tokens += part_tokens
                else:
                    break
            if yes_parts:
                lines.append("YES:" + "|".join(yes_parts))

        # NO facts
        if self.contradicting_facts:
            no_parts = []
            for fact in sorted(self.contradicting_facts, key=lambda f: f.confidence, reverse=True):
                part = f"{fact.text[:50]}({fact.confidence:.2f})"
                part_tokens = len(part.split())
                if tokens + part_tokens <= budget:
                    no_parts.append(part)
                    tokens += part_tokens
                else:
                    break
            if no_parts:
                lines.append("NO:" + "|".join(no_parts))

        return " ".join(lines)

    def to_json(self) -> str:
        """Convert to JSON graph format with nodes and edges"""
        nodes = []
        edges = []

        # Create market node (central node)
        nodes.append({
            "id": "market",
            "type": "market",
            "text": self.market.question,
            "protected_terms": self.market.protected_terms
        })

        # Create fact nodes
        for i, fact in enumerate(self.facts):
            node_id = f"fact_{i}"

            # Determine direction
            if fact.relation_to_market == "supports":
                direction = "YES"
            elif fact.relation_to_market == "contradicts":
                direction = "NO"
            else:
                direction = "NEUTRAL"

            nodes.append({
                "id": node_id,
                "type": "fact",
                "source": fact.source_type,
                "text": fact.text,
                "confidence": round(fact.confidence, 2),
                "direction": direction
            })

            # Create edge from fact to market
            edges.append({
                "from": node_id,
                "to": "market",
                "type": fact.relation_to_market,
                "strength": round(fact.relation_strength, 2)
            })

        # Create fact-to-fact edges (contradicts between YES and NO facts)
        for i, fact1 in enumerate(self.facts):
            for j, fact2 in enumerate(self.facts):
                if i >= j:
                    continue

                # If one supports and other contradicts, they contradict each other
                if (fact1.relation_to_market == "supports" and fact2.relation_to_market == "contradicts") or \
                   (fact1.relation_to_market == "contradicts" and fact2.relation_to_market == "supports"):
                    edges.append({
                        "from": f"fact_{i}",
                        "to": f"fact_{j}",
                        "type": "contradicts",
                        "strength": 0.8
                    })

        graph = {
            "nodes": nodes,
            "edges": edges,
            "metrics": {
                "total_facts": len(self.facts),
                "supporting": len(self.supporting_facts),
                "contradicting": len(self.contradicting_facts),
                "neutral": len(self.neutral_facts)
            }
        }
        return json.dumps(graph, separators=(',', ':'))


class IntelligentCompressor:
    """
    Intelligent compression that parses rough noisy text
    """

    POSITIVE_SIGNALS = {
        "won", "wins", "winning", "beat", "defeated", "victory", "strong", "healthy",
        "excellent", "favored", "favorite", "approved", "passed", "positive", "growth",
        "increase", "gains", "leading", "ahead", "success", "outperformed"
    }

    NEGATIVE_SIGNALS = {
        "lost", "loses", "losing", "defeated by", "injured", "questionable", "doubtful",
        "weak", "struggling", "failed", "rejected", "negative", "decline", "decrease",
        "losses", "trailing", "behind", "underdog", "unlikely"
    }

    def __init__(self):
        self.stats = {
            "chunks_parsed": 0,
            "facts_extracted": 0,
            "json_parses": 0,
            "html_parses": 0,
            "text_parses": 0
        }

    def compress(
        self,
        market_question: str,
        protected_terms: List[str],
        evidence_chunks: List[Dict[str, Any]],
        token_budget: int = 200,
        output_format: str = "text"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Main compression pipeline

        Returns:
            (compressed_output, metrics)
        """
        # Create market node
        market = MarketNode(
            question=market_question,
            protected_terms=protected_terms or []
        )

        # Parse all chunks and extract facts
        all_facts = []
        raw_tokens = 0

        for chunk in evidence_chunks:
            text = chunk.get("text", "")
            raw_tokens += len(text.split())

            # Parse noisy text
            facts = self._parse_noisy_text(
                text=text,
                source_type=chunk.get("source_type", "unknown"),
                source_url=chunk.get("source_url"),
                base_confidence=chunk.get("confidence", 0.8)
            )

            # Classify relationship to market
            for fact in facts:
                fact.relation_to_market, fact.relation_strength = self._classify_relationship(
                    fact, market_question, protected_terms
                )

            all_facts.extend(facts)
            self.stats["chunks_parsed"] += 1

        self.stats["facts_extracted"] = len(all_facts)

        # Deduplicate and merge similar facts
        unique_facts = self._deduplicate_facts(all_facts)

        # Delete low-confidence facts
        high_quality_facts = self._filter_by_confidence(unique_facts, min_confidence=0.3)

        # Build compressed graph
        compressed_graph = self._build_graph(market, high_quality_facts)

        # Generate output
        if output_format == "json":
            output = compressed_graph.to_json()
        else:
            output = compressed_graph.to_text(budget=token_budget)

        # Calculate metrics
        compressed_tokens = len(output.split())

        metrics = {
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(raw_tokens / compressed_tokens, 2) if compressed_tokens > 0 else 0,
            "facts_extracted": len(all_facts),
            "facts_after_dedup": len(unique_facts),
            "facts_final": len(high_quality_facts),
            "supporting_facts": len(compressed_graph.supporting_facts),
            "contradicting_facts": len(compressed_graph.contradicting_facts),
            "neutral_facts": len(compressed_graph.neutral_facts),
            "chunks_processed": self.stats["chunks_parsed"],
            "json_parses": self.stats["json_parses"],
            "html_parses": self.stats["html_parses"],
            "text_parses": self.stats["text_parses"]
        }

        return output, metrics

    def _parse_noisy_text(
        self,
        text: str,
        source_type: str,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Parse rough noisy text into clean facts"""
        facts = []

        # Try JSON parsing first
        if self._is_json(text):
            self.stats["json_parses"] += 1
            facts.extend(self._extract_facts_from_json(text, source_type, source_url, base_confidence))

        # Try HTML parsing
        elif self._is_html(text):
            self.stats["html_parses"] += 1
            facts.extend(self._extract_facts_from_html(text, source_type, source_url, base_confidence))

        # Fall back to text extraction
        if not facts:
            self.stats["text_parses"] += 1
            facts.extend(self._extract_facts_from_text(text, source_type, source_url, base_confidence))

        return facts

    def _is_json(self, text: str) -> bool:
        """Check if text is JSON"""
        text = text.strip()
        return (text.startswith('{') or text.startswith('['))

    def _is_html(self, text: str) -> bool:
        """Check if text is HTML"""
        return bool(re.search(r'<[^>]+>', text))

    def _extract_facts_from_json(
        self,
        text: str,
        source_type: str,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Extract facts from JSON data"""
        facts = []

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return facts

        # Sports video specific parsing
        if source_type == "sports_video":
            facts.extend(self._parse_sports_json(data, source_url, base_confidence))

        # Financial research specific parsing
        elif source_type == "financial_research":
            facts.extend(self._parse_financial_json(data, source_url, base_confidence))

        # Generic JSON parsing
        else:
            facts.extend(self._parse_generic_json(data, source_type, source_url, base_confidence))

        return facts

    def _parse_sports_json(
        self,
        data: Dict,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Parse ESPN-style sports JSON"""
        facts = []

        # Extract game scores
        if "game" in data or "competitors" in data:
            score_fact = self._extract_score(data)
            if score_fact:
                facts.append(ExtractedFact(
                    text=score_fact,
                    confidence=min(base_confidence + 0.1, 0.95),
                    source_type="sports_video",
                    source_url=source_url,
                    metadata={"kind": "score"}
                ))

        # Extract injuries
        if "injuries" in data:
            for injury in data.get("injuries", []):
                if isinstance(injury, dict):
                    player = injury.get("player", "")
                    status = injury.get("status", "injured")
                    if player:
                        facts.append(ExtractedFact(
                            text=f"{player} {status}",
                            confidence=base_confidence,
                            source_type="sports_video",
                            source_url=source_url,
                            metadata={"kind": "injury"}
                        ))

        # Extract odds
        if "odds" in data:
            odds_data = data["odds"]
            if isinstance(odds_data, dict):
                favorite = odds_data.get("favorite", "")
                line = odds_data.get("line", "")
                if favorite:
                    facts.append(ExtractedFact(
                        text=f"Betting odds favor {favorite}" + (f" at {line}" if line else ""),
                        confidence=base_confidence - 0.1,
                        source_type="sports_video",
                        source_url=source_url,
                        metadata={"kind": "odds"}
                    ))

        return facts

    def _parse_financial_json(
        self,
        data: Dict,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Parse Kalshi-style financial JSON"""
        facts = []

        # Extract market price
        if "market_price" in data or "yes_price" in data:
            yes_price = data.get("yes_price") or data.get("market_price")
            if yes_price:
                facts.append(ExtractedFact(
                    text=f"Market price: {yes_price}",
                    confidence=base_confidence,
                    source_type="financial_research",
                    source_url=source_url,
                    metadata={"kind": "price"}
                ))

        # Extract volume
        if "volume" in data:
            volume = data["volume"]
            facts.append(ExtractedFact(
                text=f"Trading volume: {volume}",
                confidence=base_confidence - 0.2,
                source_type="financial_research",
                source_url=source_url,
                metadata={"kind": "volume"}
            ))

        return facts

    def _parse_generic_json(
        self,
        data: Any,
        source_type: str,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Generic JSON parsing - extract text values"""
        facts = []

        def extract_text_values(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and len(value) > 20 and len(value) < 500:
                        # Looks like a meaningful text snippet
                        facts.append(ExtractedFact(
                            text=value[:200],
                            confidence=base_confidence - 0.2,
                            source_type=source_type,
                            source_url=source_url,
                            metadata={"json_key": key}
                        ))
                    elif isinstance(value, (dict, list)):
                        extract_text_values(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_text_values(item, f"{path}[{i}]")

        extract_text_values(data)
        return facts[:10]  # Limit to 10 facts per chunk

    def _extract_facts_from_html(
        self,
        text: str,
        source_type: str,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Extract facts from HTML"""
        facts = []

        try:
            soup = BeautifulSoup(text, 'html.parser')

            # Extract from paragraphs
            for p in soup.find_all('p'):
                text_content = p.get_text().strip()
                if len(text_content) > 30:
                    sentences = re.split(r'[.!?]+', text_content)
                    for sent in sentences:
                        sent = sent.strip()
                        if len(sent) > 20:
                            facts.append(ExtractedFact(
                                text=sent[:200],
                                confidence=base_confidence - 0.15,
                                source_type=source_type,
                                source_url=source_url,
                                metadata={"source": "html_p"}
                            ))

            # Extract from headers
            for h in soup.find_all(['h1', 'h2', 'h3']):
                text_content = h.get_text().strip()
                if len(text_content) > 10:
                    facts.append(ExtractedFact(
                        text=text_content[:200],
                        confidence=base_confidence - 0.1,
                        source_type=source_type,
                        source_url=source_url,
                        metadata={"source": "html_header"}
                    ))

        except Exception:
            pass

        return facts[:10]  # Limit

    def _extract_facts_from_text(
        self,
        text: str,
        source_type: str,
        source_url: Optional[str],
        base_confidence: float
    ) -> List[ExtractedFact]:
        """Extract facts from plain text"""
        facts = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        for sent in sentences:
            sent = sent.strip()

            # Skip very short or very long sentences
            if len(sent) < 20 or len(sent) > 500:
                continue

            # Skip sentences that are likely noise
            if sent.startswith(('http', 'www', '{', '[', '<')):
                continue

            # Extract as fact
            facts.append(ExtractedFact(
                text=sent[:200],
                confidence=base_confidence - 0.2,
                source_type=source_type,
                source_url=source_url,
                metadata={"source": "text"}
            ))

        return facts[:15]  # Limit

    def _extract_score(self, data: Dict) -> Optional[str]:
        """Extract game score from JSON"""
        try:
            if "game" in data:
                game = data["game"]
                if "competitors" in game:
                    comps = game["competitors"]
                    if len(comps) >= 2:
                        team1 = comps[0].get("team", "Team1")
                        score1 = comps[0].get("score", "")
                        team2 = comps[1].get("team", "Team2")
                        score2 = comps[1].get("score", "")
                        if score1 and score2:
                            return f"{team1} {score1}-{score2} {team2}"

            if "competitors" in data:
                comps = data["competitors"]
                if len(comps) >= 2:
                    team1 = comps[0].get("name") or comps[0].get("team", "Team1")
                    score1 = comps[0].get("score", "")
                    team2 = comps[1].get("name") or comps[1].get("team", "Team2")
                    score2 = comps[1].get("score", "")
                    if score1 and score2:
                        return f"{team1} {score1}-{score2} {team2}"
        except Exception:
            pass

        return None

    def _classify_relationship(
        self,
        fact: ExtractedFact,
        market_question: str,
        protected_terms: List[str]
    ) -> Tuple[str, float]:
        """
        Classify how fact relates to market question
        Returns: (relation_type, strength)
        """
        fact_lower = fact.text.lower()
        question_lower = market_question.lower()

        # Check relevance to protected terms
        relevance_score = 0
        for term in protected_terms:
            if term.lower() in fact_lower:
                relevance_score += 1

        # If not relevant, mark as neutral
        if relevance_score == 0:
            return ("neutral", 0.3)

        # Count positive and negative signals
        fact_words = set(fact_lower.split())
        yes_count = len(fact_words & self.POSITIVE_SIGNALS)
        no_count = len(fact_words & self.NEGATIVE_SIGNALS)

        # Classify
        if yes_count > no_count:
            strength = min(0.5 + (yes_count * 0.1) + (relevance_score * 0.1), 0.95)
            return ("supports", strength)
        elif no_count > yes_count:
            strength = min(0.5 + (no_count * 0.1) + (relevance_score * 0.1), 0.95)
            return ("contradicts", strength)
        else:
            strength = 0.4 + (relevance_score * 0.1)
            return ("neutral", strength)

    def _deduplicate_facts(self, facts: List[ExtractedFact]) -> List[ExtractedFact]:
        """Remove duplicate or very similar facts"""
        if not facts:
            return facts

        unique = []
        seen_texts = set()

        for fact in facts:
            # Normalize text for comparison
            normalized = re.sub(r'\s+', ' ', fact.text.lower().strip())

            # Check for exact duplicates
            if normalized in seen_texts:
                continue

            # Check for high similarity with existing facts
            is_duplicate = False
            for existing_text in seen_texts:
                # Simple token overlap check
                tokens1 = set(normalized.split())
                tokens2 = set(existing_text.split())
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2) if tokens1 or tokens2 else 0

                if overlap > 0.8:  # Very similar
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(fact)
                seen_texts.add(normalized)

        return unique

    def _filter_by_confidence(
        self,
        facts: List[ExtractedFact],
        min_confidence: float = 0.3
    ) -> List[ExtractedFact]:
        """Filter out low-confidence facts"""
        return [f for f in facts if f.confidence >= min_confidence]

    def _build_graph(
        self,
        market: MarketNode,
        facts: List[ExtractedFact]
    ) -> CompressedGraph:
        """Build market-centric compressed graph"""

        # Separate by relationship
        supporting = [f for f in facts if f.relation_to_market == "supports"]
        contradicting = [f for f in facts if f.relation_to_market == "contradicts"]
        neutral = [f for f in facts if f.relation_to_market == "neutral"]

        # Sort by confidence
        supporting.sort(key=lambda f: f.confidence, reverse=True)
        contradicting.sort(key=lambda f: f.confidence, reverse=True)
        neutral.sort(key=lambda f: f.confidence, reverse=True)

        return CompressedGraph(
            market=market,
            facts=facts,
            supporting_facts=supporting,
            contradicting_facts=contradicting,
            neutral_facts=neutral
        )
