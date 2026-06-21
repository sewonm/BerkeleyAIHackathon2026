#!/usr/bin/env python3
"""
Graph Compression Visualizer

Visualizes graph compression agent output using pyvis (interactive) or graphviz (static).

Usage:
    # Interactive HTML visualization
    python visualize_graph.py --input graph_output.json --output graph.html --type interactive

    # Static PNG visualization
    python visualize_graph.py --input graph_output.json --output graph.png --type static

    # Both
    python visualize_graph.py --input graph_output.json --output graph --type both
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any


def visualize_interactive(graph_data: Dict[str, Any], output_path: str):
    """Create interactive HTML visualization with pyvis"""
    try:
        from pyvis.network import Network
    except ImportError:
        print("ERROR: pyvis not installed. Run: pip install pyvis")
        return False

    # Create network
    net = Network(
        height="800px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        directed=True,
        notebook=False
    )

    # Configure physics for better layout
    net.barnes_hut(
        gravity=-80000,
        central_gravity=0.3,
        spring_length=250,
        spring_strength=0.001,
        damping=0.09,
        overlap=0
    )

    # Add nodes
    for node in graph_data.get("nodes", []):
        node_id = node["id"]

        # Color by direction
        if node["dir"] == "Y":
            color = "#00ff00"  # Green for YES
        elif node["dir"] == "N":
            color = "#ff0000"  # Red for NO
        else:
            color = "#ffff00"  # Yellow for NEUTRAL

        # Size by score (10px base + up to 30px for score)
        size = 10 + (node.get("score", 0.5) * 30)

        # Label with text snippet + score
        text_preview = node.get("text", "")[:40]
        if len(node.get("text", "")) > 40:
            text_preview += "..."

        label = f"{node['source']}\n{text_preview}\n★{node.get('score', 0):.2f}"

        # Title (hover text) - full information
        title = f"""
Source: {node['source']}
Direction: {node['dir']}
Score: {node.get('score', 0):.2f}
Merged: {node.get('merged', 0)}

Text:
{node.get('text', 'N/A')}
        """.strip()

        net.add_node(
            node_id,
            label=label,
            color=color,
            size=size,
            title=title,
            shape="dot"
        )

    # Add edges
    for edge in graph_data.get("edges", []):
        # Color by relationship type
        if edge["type"] == "reinforces":
            edge_color = "#00ff00"
            edge_label = "reinforces"
        elif edge["type"] == "contradicts":
            edge_color = "#ff0000"
            edge_label = "contradicts"
        else:  # same_sentiment
            edge_color = "#ffaa00"
            edge_label = "same"

        # Width by strength
        width = 1 + (edge.get("strength", 0.5) * 5)

        # Title (hover text)
        edge_title = f"{edge['type']} (strength: {edge.get('strength', 0):.2f})"

        net.add_edge(
            edge["from"],
            edge["to"],
            label=edge_label,
            color=edge_color,
            width=width,
            title=edge_title
        )

    # Add custom controls
    net.show_buttons(filter_=['physics'])

    # Save
    net.write_html(output_path)
    print(f"✓ Interactive visualization saved to: {output_path}")
    print(f"  Open in browser to explore: file://{Path(output_path).absolute()}")
    return True


def visualize_static(graph_data: Dict[str, Any], output_path: str):
    """Create static image with graphviz"""
    try:
        from graphviz import Digraph
    except ImportError:
        print("ERROR: graphviz not installed. Run: pip install graphviz")
        print("       Also install binary: brew install graphviz")
        return False

    # Determine format from output path
    if output_path.endswith('.svg'):
        fmt = 'svg'
    elif output_path.endswith('.pdf'):
        fmt = 'pdf'
    else:
        fmt = 'png'
        if not output_path.endswith('.png'):
            output_path = output_path + '.png'

    dot = Digraph(comment="Graph Compression", format=fmt)
    dot.attr(rankdir="LR", bgcolor="white", splines="ortho")
    dot.attr("node", style="filled,rounded", fontsize="10", fontname="Arial")
    dot.attr("edge", fontsize="8", fontname="Arial")

    # Add nodes
    for node in graph_data.get("nodes", []):
        node_id = node["id"]

        # Color by direction
        if node["dir"] == "Y":
            fillcolor = "lightgreen"
            fontcolor = "darkgreen"
        elif node["dir"] == "N":
            fillcolor = "lightcoral"
            fontcolor = "darkred"
        else:
            fillcolor = "lightyellow"
            fontcolor = "darkgoldenrod"

        # Label - truncate text for readability
        text_preview = node.get("text", "")[:50]
        if len(node.get("text", "")) > 50:
            text_preview += "..."

        label = f"{node['source']}\\n{text_preview}\\n★ {node.get('score', 0):.2f}"

        # Determine node size by score
        width = str(2 + node.get("score", 0.5))
        height = str(1 + node.get("score", 0.5) * 0.5)

        dot.node(
            node_id,
            label=label,
            fillcolor=fillcolor,
            fontcolor=fontcolor,
            shape="box",
            width=width,
            height=height
        )

    # Add edges
    for edge in graph_data.get("edges", []):
        # Color and style by type
        if edge["type"] == "reinforces":
            color = "green"
            style = "solid"
        elif edge["type"] == "contradicts":
            color = "red"
            style = "bold"
        else:
            color = "orange"
            style = "dashed"

        # Width by strength
        penwidth = str(1 + edge.get("strength", 0.5) * 3)

        dot.edge(
            edge["from"],
            edge["to"],
            label=edge["type"],
            color=color,
            style=style,
            penwidth=penwidth
        )

    # Render
    try:
        output_base = output_path.replace('.png', '').replace('.svg', '').replace('.pdf', '')
        dot.render(output_base, format=fmt, cleanup=True)
        print(f"✓ Static visualization saved to: {output_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to render graphviz: {e}")
        print("Make sure graphviz binary is installed: brew install graphviz")
        return False


def load_graph_data(input_path: str) -> Dict[str, Any]:
    """Load graph data from JSON file"""
    try:
        with open(input_path, "r") as f:
            data = json.load(f)

        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("Graph data must be a JSON object")

        if "nodes" not in data:
            raise ValueError("Graph data must have 'nodes' field")

        if "edges" not in data:
            # Edges are optional
            data["edges"] = []

        return data

    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in input file: {e}")
        raise
    except Exception as e:
        print(f"ERROR: Failed to load graph data: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Visualize graph compression output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive HTML visualization
  python visualize_graph.py --input graph.json --output viz.html --type interactive

  # Static PNG image
  python visualize_graph.py --input graph.json --output viz.png --type static

  # Both interactive and static
  python visualize_graph.py --input graph.json --output viz --type both
        """
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file with graph data (must have 'nodes' and 'edges' fields)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path (extension determines format for static)"
    )
    parser.add_argument(
        "--type",
        choices=["interactive", "static", "both"],
        default="interactive",
        help="Visualization type (default: interactive)"
    )

    args = parser.parse_args()

    # Load graph data
    print(f"Loading graph data from: {args.input}")
    try:
        graph_data = load_graph_data(args.input)
    except Exception:
        return 1

    node_count = len(graph_data.get("nodes", []))
    edge_count = len(graph_data.get("edges", []))
    print(f"  Loaded: {node_count} nodes, {edge_count} edges")

    if node_count == 0:
        print("WARNING: No nodes found in graph data")
        return 1

    # Generate visualizations
    success = True

    if args.type in ["interactive", "both"]:
        output_html = args.output if args.output.endswith(".html") else f"{args.output}.html"
        print(f"\nGenerating interactive visualization...")
        if not visualize_interactive(graph_data, output_html):
            success = False

    if args.type in ["static", "both"]:
        # Determine extension
        if args.output.endswith(('.png', '.svg', '.pdf')):
            output_static = args.output
        else:
            output_static = f"{args.output}.png"

        print(f"\nGenerating static visualization...")
        if not visualize_static(graph_data, output_static):
            success = False

    if success:
        print(f"\n✓ Visualization complete!")
        return 0
    else:
        print(f"\n✗ Some visualizations failed")
        return 1


if __name__ == "__main__":
    exit(main())
