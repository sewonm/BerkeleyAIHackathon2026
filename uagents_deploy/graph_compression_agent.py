"""
Graph Compression Agent - Deployed Fetch.ai uAgent for evidence graph compression

Takes evidence chunks from multiple sources, builds a graph with:
- Nodes: Evidence sources (sports_video_agent, news_agent, etc.)
- Edges: Relationships (contradicts, reinforces, same_sentiment)
- Compression: Merges redundant sources, deletes low-value ones, outputs compact graph

Dual-protocol agent:
  1. Chat Protocol v0.3.0 (ASI:One discoverable)
  2. Custom CompressionRequest protocol (orchestrator compat)

DEPLOY AS MAILBOX AGENT:
    python uagents_deploy/graph_compression_agent.py
"""

import os
import json
import re
import asyncio
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from uagents import Agent, Context, Protocol, Model
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

# ============================================================================
# DATA MODELS
# ============================================================================

class EvidenceChunk(Model):
    """Input: One chunk per source"""
    chunk_id: str
    market_id: str
    source_agent: str
    source_type: str
    text: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CompressionRequest(Model):
    """Request to compress evidence"""
    request_id: str
    market_id: str
    market_question: str
    resolution_criteria: str = ""
    evidence_chunks: List[EvidenceChunk]
    token_budget: int = 200
    output_format: str = "text"  # "text" or "json"


class CompressionResponse(Model):
    """Response with compressed graph"""
    request_id: str
    market_id: str
    status: str  # "success" or "error"
    compressed_output: str
    metrics: Dict[str, Any]
    error: Optional[str] = None


# ============================================================================
# GRAPH COMPRESSION ENGINE
# ============================================================================

@dataclass
class SourceNode:
    """A source of evidence (one chunk)"""
    node_id: str
    source_agent: str
    text: str
    score: float = 0.0  # Information value
    direction: str = "NEUTRAL"  # YES, NO, NEUTRAL
    merged_with: List[str] = field(default_factory=list)
    deleted: bool = False


@dataclass
class RelationshipEdge:
    """Relationship between sources"""
    from_id: str
    to_id: str
    relation_type: str  # "reinforces", "contradicts", "same_sentiment"
    strength: float = 1.0


class GraphCompressor:
    """Compresses evidence chunks into a graph with relationships"""

    YES_SIGNALS = {
        "won", "wins", "winning", "leads", "beat", "defeated", "strong",
        "excellent", "healthy", "positive", "increase", "growth", "approved"
    }

    NO_SIGNALS = {
        "lost", "loses", "losing", "injured", "struggled", "weak", "negative",
        "decline", "decrease", "failed", "rejected", "questionable"
    }

    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold

    def compress(
        self,
        evidence_chunks: List[Dict[str, Any]],
        market_question: str,
        token_budget: int = 200,
        output_format: str = "text"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compress evidence chunks into graph format

        Returns:
            (compressed_output, metrics)
        """
        # Step 1: Create source nodes (one per chunk)
        nodes = self._create_source_nodes(evidence_chunks)
        initial_count = len(nodes)

        # Step 2: Score each node
        nodes = self._score_nodes(nodes, market_question)

        # Step 3: Build relationship edges
        edges = self._build_relationship_edges(nodes)

        # Step 4: Merge similar nodes (based on edges)
        nodes, edges = self._merge_similar_nodes(nodes, edges)

        # Step 5: Delete low-value nodes
        nodes = self._delete_low_value_nodes(nodes, keep_top_n=10)

        # Step 6: Reinforce high-agreement clusters
        nodes, edges = self._reinforce_clusters(nodes, edges)

        # Step 7: Generate output
        if output_format == "json":
            output = self._generate_json_output(nodes, edges)
        else:
            output = self._generate_text_output(nodes, edges, token_budget)

        # Calculate metrics
        raw_tokens = sum(len(chunk.get("text", "").split()) for chunk in evidence_chunks)
        compressed_tokens = len(output.split()) if isinstance(output, str) else len(json.dumps(output).split())

        metrics = {
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(raw_tokens / compressed_tokens, 2) if compressed_tokens > 0 else 0,
            "initial_sources": initial_count,
            "merged_sources": sum(1 for n in nodes if len(n.merged_with) > 0),
            "deleted_sources": sum(1 for n in nodes if n.deleted),
            "final_sources": len([n for n in nodes if not n.deleted]),
            "relationships": len(edges),
            "yes_sources": len([n for n in nodes if n.direction == "YES" and not n.deleted]),
            "no_sources": len([n for n in nodes if n.direction == "NO" and not n.deleted]),
        }

        return output, metrics

    def _create_source_nodes(self, chunks: List[Dict[str, Any]]) -> List[SourceNode]:
        """Create one node per source chunk"""
        nodes = []
        for chunk in chunks:
            text = chunk.get("text", "")
            # Clean up text
            text = re.sub(r'\s+', ' ', text).strip()

            node = SourceNode(
                node_id=chunk.get("chunk_id", str(uuid4())),
                source_agent=chunk.get("source_agent", "unknown"),
                text=text,
                direction=self._classify_direction(text)
            )
            nodes.append(node)
        return nodes

    def _score_nodes(self, nodes: List[SourceNode], market_question: str) -> List[SourceNode]:
        """Score each node by information value"""
        for node in nodes:
            score = 0.0

            # Has numbers
            if re.search(r'\d+', node.text):
                score += 0.3

            # Has signal words
            text_words = set(node.text.lower().split())
            signal_count = len(text_words & (self.YES_SIGNALS | self.NO_SIGNALS))
            score += min(signal_count * 0.15, 0.3)

            # Has named entities
            if re.search(r'\b[A-Z][a-z]+', node.text):
                score += 0.2

            # Strong direction
            if node.direction != "NEUTRAL":
                score += 0.1

            # Text length (prefer 20-100 words)
            word_count = len(node.text.split())
            if 20 <= word_count <= 100:
                score += 0.1

            node.score = min(score, 1.0)

        return nodes

    def _build_relationship_edges(self, nodes: List[SourceNode]) -> List[RelationshipEdge]:
        """Build edges between nodes based on relationships"""
        edges = []

        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes[i+1:], start=i+1):
                # Calculate similarity
                tokens1 = set(node1.text.lower().split())
                tokens2 = set(node2.text.lower().split())
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2) if tokens1 or tokens2 else 0

                # Same sentiment (high overlap)
                if overlap >= self.similarity_threshold:
                    edges.append(RelationshipEdge(
                        from_id=node1.node_id,
                        to_id=node2.node_id,
                        relation_type="same_sentiment",
                        strength=overlap
                    ))

                # Reinforces (same direction, moderate overlap)
                elif overlap >= 0.3 and node1.direction == node2.direction and node1.direction != "NEUTRAL":
                    edges.append(RelationshipEdge(
                        from_id=node1.node_id,
                        to_id=node2.node_id,
                        relation_type="reinforces",
                        strength=overlap
                    ))

                # Contradicts (opposite directions)
                elif (node1.direction == "YES" and node2.direction == "NO") or \
                     (node1.direction == "NO" and node2.direction == "YES"):
                    edges.append(RelationshipEdge(
                        from_id=node1.node_id,
                        to_id=node2.node_id,
                        relation_type="contradicts",
                        strength=0.8
                    ))

        return edges

    def _merge_similar_nodes(
        self,
        nodes: List[SourceNode],
        edges: List[RelationshipEdge]
    ) -> Tuple[List[SourceNode], List[RelationshipEdge]]:
        """Merge nodes with same_sentiment relationships"""
        node_map = {n.node_id: n for n in nodes}

        # Find same_sentiment edges
        for edge in edges:
            if edge.relation_type == "same_sentiment":
                from_node = node_map.get(edge.from_id)
                to_node = node_map.get(edge.to_id)

                if from_node and to_node and not to_node.deleted:
                    # Merge to_node into from_node (keep higher score)
                    if from_node.score >= to_node.score:
                        from_node.merged_with.append(to_node.node_id)
                        to_node.deleted = True
                    else:
                        to_node.merged_with.append(from_node.node_id)
                        from_node.deleted = True

        # Remove edges involving deleted nodes
        edges = [e for e in edges if not node_map.get(e.from_id, SourceNode("", "", "", deleted=True)).deleted
                 and not node_map.get(e.to_id, SourceNode("", "", "", deleted=True)).deleted]

        return nodes, edges

    def _delete_low_value_nodes(self, nodes: List[SourceNode], keep_top_n: int = 10) -> List[SourceNode]:
        """Delete nodes with low information value"""
        # Sort by score
        active_nodes = [n for n in nodes if not n.deleted]
        active_nodes.sort(key=lambda n: n.score, reverse=True)

        # Keep only top N
        keep_ids = set(n.node_id for n in active_nodes[:keep_top_n])

        for node in nodes:
            if node.node_id not in keep_ids and not node.deleted:
                node.deleted = True

        return nodes

    def _reinforce_clusters(
        self,
        nodes: List[SourceNode],
        edges: List[RelationshipEdge]
    ) -> Tuple[List[SourceNode], List[RelationshipEdge]]:
        """Boost scores of nodes in high-agreement clusters"""
        node_map = {n.node_id: n for n in nodes}

        # Count reinforcement edges per node
        reinforcement_count = {}
        for edge in edges:
            if edge.relation_type == "reinforces":
                reinforcement_count[edge.from_id] = reinforcement_count.get(edge.from_id, 0) + 1
                reinforcement_count[edge.to_id] = reinforcement_count.get(edge.to_id, 0) + 1

        # Boost scores
        for node_id, count in reinforcement_count.items():
            node = node_map.get(node_id)
            if node and not node.deleted:
                boost = min(count * 0.05, 0.2)
                node.score = min(node.score + boost, 1.0)

        return nodes, edges

    def _generate_text_output(
        self,
        nodes: List[SourceNode],
        edges: List[RelationshipEdge],
        token_budget: int
    ) -> str:
        """Generate ultra-compact text output"""
        active_nodes = [n for n in nodes if not n.deleted]
        active_nodes.sort(key=lambda n: n.score, reverse=True)

        yes_nodes = [n for n in active_nodes if n.direction == "YES"]
        no_nodes = [n for n in active_nodes if n.direction == "NO"]

        lines = []
        tokens_used = 0

        # YES claims
        if yes_nodes:
            yes_parts = []
            for node in yes_nodes:
                # Shorten text
                short_text = node.text[:50]
                claim_str = f"{short_text}({node.score:.2f})"
                tokens = len(claim_str.split())

                if tokens_used + tokens <= token_budget:
                    yes_parts.append(claim_str)
                    tokens_used += tokens

            if yes_parts:
                lines.append("YES:" + "|".join(yes_parts))

        # NO claims
        if no_nodes:
            no_parts = []
            for node in no_nodes:
                short_text = node.text[:50]
                claim_str = f"{short_text}({node.score:.2f})"
                tokens = len(claim_str.split())

                if tokens_used + tokens <= token_budget:
                    no_parts.append(claim_str)
                    tokens_used += tokens

            if no_parts:
                lines.append("NO:" + "|".join(no_parts))

        return " ".join(lines)

    def _generate_json_output(
        self,
        nodes: List[SourceNode],
        edges: List[RelationshipEdge]
    ) -> str:
        """Generate JSON graph output"""
        active_nodes = [n for n in nodes if not n.deleted]

        output = {
            "nodes": [
                {
                    "id": n.node_id,
                    "source": n.source_agent,
                    "text": n.text[:80],
                    "dir": n.direction[0],  # Y, N, or NE
                    "score": round(n.score, 2),
                    "merged": len(n.merged_with)
                }
                for n in active_nodes
            ],
            "edges": [
                {
                    "from": e.from_id,
                    "to": e.to_id,
                    "type": e.relation_type,
                    "strength": round(e.strength, 2)
                }
                for e in edges
            ]
        }

        return json.dumps(output, separators=(',', ':'))

    def _classify_direction(self, text: str) -> str:
        """Classify YES, NO, or NEUTRAL"""
        text_words = set(text.lower().split())
        yes_count = len(text_words & self.YES_SIGNALS)
        no_count = len(text_words & self.NO_SIGNALS)

        if yes_count > no_count:
            return "YES"
        elif no_count > yes_count:
            return "NO"
        else:
            return "NEUTRAL"


# ============================================================================
# UAGENT SETUP
# ============================================================================

AGENT_NAME = "graph_compression_agent"
AGENT_SEED = os.getenv("GRAPH_COMPRESSION_AGENT_SEED", "graph-compression-agent-seed-v1")
AGENT_PORT = 8005
AGENT_MAILBOX = True
AGENT_DESCRIPTION = (
    "Graph Compression Agent — takes evidence chunks from multiple sources, builds "
    "a graph with relationship edges (contradicts, reinforces, same_sentiment), "
    "merges redundant sources, deletes low-value ones, and outputs compressed graph."
)

README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GRAPH_COMPRESSION_README.md")

_agent_kwargs = dict(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=AGENT_MAILBOX,
    description=AGENT_DESCRIPTION,
    publish_agent_details=True,
)
if os.path.exists(README_PATH):
    _agent_kwargs["readme_path"] = README_PATH

agent = Agent(**_agent_kwargs)

# Create compressor instance
compressor = GraphCompressor(similarity_threshold=0.6)


# ============================================================================
# CHAT PROTOCOL (ASI:One)
# ============================================================================

chat_protocol = Protocol(spec=chat_protocol_spec)


@chat_protocol.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle chat messages from ASI:One"""
    try:
        # ACK first
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

        # Extract text
        try:
            user_text = msg.text()
        except Exception:
            user_text = ""

        # Strip @mentions
        user_text = re.sub(r'^@[\w-]+\s+', '', user_text.strip())

        ctx.logger.info(f"[{AGENT_NAME}] Chat from {sender}: {user_text[:100]}...")

        # Try to parse as JSON request
        try:
            request_data = json.loads(user_text)

            # Build compression request - convert evidence chunks to dicts
            evidence_chunks = []
            for chunk in request_data.get("evidence_chunks", []):
                if isinstance(chunk, dict):
                    evidence_chunks.append(chunk)

            output_format = request_data.get("output_format", "text")

            compressed_output, metrics = compressor.compress(
                evidence_chunks=evidence_chunks,
                market_question=request_data.get("market_question", ""),
                token_budget=request_data.get("token_budget", 200),
                output_format=output_format
            )

            # Format response
            response_text = f"""
**Graph Compression Complete** 🗜️

**Metrics:**
- Raw tokens: {metrics['raw_tokens']}
- Compressed tokens: {metrics['compressed_tokens']}
- **Compression ratio: {metrics['compression_ratio']}x**
- Initial sources: {metrics['initial_sources']}
- Merged: {metrics['merged_sources']}
- Deleted: {metrics['deleted_sources']}
- Final sources: {metrics['final_sources']}
- Relationships: {metrics['relationships']}
- YES sources: {metrics['yes_sources']}
- NO sources: {metrics['no_sources']}

**Compressed Output:**
```
{compressed_output}
```
"""

            response_msg = ChatMessage(content=[TextContent(text=response_text)])
            await ctx.send(sender, response_msg)

        except json.JSONDecodeError:
            # Natural language - show help
            help_text = """
**Graph Compression Agent** 🗜️

I compress evidence from multiple sources into a compact graph with relationships.

**How to use:**

Send JSON with:
```json
{
  "market_question": "Your market question",
  "evidence_chunks": [
    {
      "chunk_id": "1",
      "market_id": "test",
      "source_agent": "sports_video_agent",
      "source_type": "sports",
      "text": "France beat Brazil 2-1..."
    }
  ],
  "token_budget": 200,
  "output_format": "text"
}
```

**What I do:**
1. Create source nodes (one per chunk)
2. Build relationship edges (contradicts, reinforces, same_sentiment)
3. Merge similar sources
4. Delete low-value sources
5. Reinforce high-agreement clusters
6. Output compressed graph

**Output formats:**
- `"text"` - Ultra-compact text (YES:claim1|claim2 NO:claim3)
- `"json"` - Graph JSON with nodes and edges
"""
            response_msg = ChatMessage(content=[TextContent(text=help_text)])
            await ctx.send(sender, response_msg)

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Chat error: {e}")
        import traceback
        ctx.logger.error(traceback.format_exc())

        error_msg = ChatMessage(content=[TextContent(text=f"Error: {str(e)}")])
        await ctx.send(sender, error_msg)


@chat_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    """Handle ACK messages"""
    ctx.logger.info(f"[{AGENT_NAME}] ACK from {sender}")


# ============================================================================
# CUSTOM PROTOCOL (Orchestrator)
# ============================================================================

compression_protocol = Protocol(name="GraphCompression")


@compression_protocol.on_message(model=CompressionRequest)
async def handle_compression_request(ctx: Context, sender: str, msg: CompressionRequest):
    """Handle compression requests from orchestrator"""
    ctx.logger.info(f"[{AGENT_NAME}] Compression request from {sender}")
    ctx.logger.info(f"Market: {msg.market_id}, Chunks: {len(msg.evidence_chunks)}")

    try:
        # Convert to dict format
        chunks = [
            {
                "chunk_id": chunk.chunk_id,
                "market_id": chunk.market_id,
                "source_agent": chunk.source_agent,
                "source_type": chunk.source_type,
                "text": chunk.text,
                "timestamp": chunk.timestamp,
                "metadata": chunk.metadata
            }
            for chunk in msg.evidence_chunks
        ]

        compressed_output, metrics = compressor.compress(
            evidence_chunks=chunks,
            market_question=msg.market_question,
            token_budget=msg.token_budget,
            output_format=msg.output_format
        )

        response = CompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="success",
            compressed_output=compressed_output,
            metrics=metrics
        )

        await ctx.send(sender, response)

        ctx.logger.info(f"[{AGENT_NAME}] Compression complete: {metrics['compression_ratio']}x")

    except Exception as e:
        ctx.logger.error(f"[{AGENT_NAME}] Compression failed: {e}")
        import traceback
        ctx.logger.error(traceback.format_exc())

        response = CompressionResponse(
            request_id=msg.request_id,
            market_id=msg.market_id,
            status="error",
            compressed_output="",
            metrics={},
            error=str(e)
        )

        await ctx.send(sender, response)


# ============================================================================
# REGISTER PROTOCOLS
# ============================================================================

agent.include(chat_protocol, publish_manifest=True)
agent.include(compression_protocol, publish_manifest=True)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(f"Starting {AGENT_NAME}")
    print(f"Agent address: {agent.address}")
    print(f"Mailbox: {AGENT_MAILBOX}")
    print("=" * 80)
    agent.run()
