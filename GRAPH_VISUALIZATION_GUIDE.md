# Graph Visualization Guide

Visualize graph compression output using `visualize_graph.py`.

## Quick Start

```bash
# Interactive HTML visualization (recommended for exploration)
python visualize_graph.py --input graph_output.json --output graph.html --type interactive

# Static PNG image (for documentation)
python visualize_graph.py --input graph_output.json --output graph.png --type static

# Both interactive and static
python visualize_graph.py --input graph_output.json --output graph --type both
```

## Installation

### Prerequisites

```bash
# Activate virtual environment
source venv/bin/activate

# Install Python packages
pip install pyvis graphviz

# Install graphviz binary (macOS)
brew install graphviz
```

## Input Format

The tool expects JSON output from `graph_compression_agent.py`:

```json
{
  "nodes": [
    {
      "id": "unique-id",
      "source": "agent_name",
      "text": "Evidence text",
      "dir": "Y",        // Y=YES (green), N=NO (red), NE=NEUTRAL (yellow)
      "score": 0.85,     // Information value 0.0-1.0 (affects node size)
      "merged": 0        // Number of merged nodes
    }
  ],
  "edges": [
    {
      "from": "node_id_1",
      "to": "node_id_2",
      "type": "reinforces",  // reinforces (green), contradicts (red), same_sentiment (orange)
      "strength": 0.7        // 0.0-1.0 (affects edge width)
    }
  ]
}
```

## Output Types

### Interactive HTML (`--type interactive`)
- **Best for**: Exploring large graphs, finding relationships
- **Features**:
  - Drag nodes to reposition
  - Zoom and pan
  - Hover for detailed info
  - Physics simulation for automatic layout
  - Adjustable physics controls
- **Opens in**: Any web browser
- **File size**: ~7KB for typical graphs

### Static Image (`--type static`)
- **Best for**: Documentation, reports, presentations
- **Features**:
  - Clean, professional layout
  - Color-coded nodes and edges
  - Truncated text labels for readability
  - Size-scaled by score
- **Formats**: PNG (default), SVG, PDF
- **File size**: ~40KB for PNG

## Visualization Features

### Node Appearance
- **Color by direction**:
  - Green = YES (supports market outcome)
  - Red = NO (contradicts market outcome)
  - Yellow = NEUTRAL
- **Size by score**: Higher scores = larger nodes
- **Label format**: `source\ntext preview...\n★score`
- **Hover text**: Full text and metadata

### Edge Appearance
- **Color by type**:
  - Green = reinforces (agrees with)
  - Red = contradicts (conflicts with)
  - Orange = same_sentiment
- **Width by strength**: Stronger relationships = thicker lines
- **Label**: Relationship type

## Examples

### Example 1: Single Graph
```bash
python visualize_graph.py \
  --input graph_output.json \
  --output viz.html \
  --type interactive
```

Output: `viz.html` - Open in browser to explore

### Example 2: Both Formats
```bash
python visualize_graph.py \
  --input graph_output.json \
  --output viz \
  --type both
```

Output:
- `viz.html` - Interactive version
- `viz.png` - Static version

### Example 3: Different Static Formats
```bash
# PNG (default)
python visualize_graph.py --input graph.json --output viz.png --type static

# SVG (scalable vector)
python visualize_graph.py --input graph.json --output viz.svg --type static

# PDF (for printing)
python visualize_graph.py --input graph.json --output viz.pdf --type static
```

## Test Example

A test graph is included in `test_graph_data.json`:

```bash
python visualize_graph.py \
  --input test_graph_data.json \
  --output test_viz \
  --type both
```

This creates:
- `test_viz.html` - Interactive graph with 5 nodes, 4 edges
- `test_viz.png` - Static image

### Test Graph Description
- **Market**: Will France win the World Cup 2026?
- **4 YES nodes**: Video evidence, betting odds, stats, team morale
- **1 NO node**: Injury concerns
- **Edges**: Reinforcements between positive evidence, contradiction from injury

## Interpreting the Graph

### Node Analysis
- **Large green nodes**: Strong YES evidence
- **Large red nodes**: Strong NO evidence
- **Small nodes**: Lower confidence/importance
- **Merged count**: How many similar nodes were combined

### Edge Analysis
- **Green reinforces**: Evidence agrees and strengthens each other
- **Red contradicts**: Evidence conflicts (investigate further)
- **Orange same_sentiment**: Same direction but not directly related
- **Thick edges**: Strong relationships
- **Thin edges**: Weak relationships

### Graph Structure Patterns
1. **Star pattern**: One central node with many connections
   - Indicates key piece of evidence
2. **Chain pattern**: Linear sequence of reinforcing evidence
   - Indicates logical progression
3. **Clusters**: Groups of interconnected nodes
   - Indicates topic areas
4. **Contradictions**: Red edges between clusters
   - Indicates conflicting information (decision uncertainty)

## Troubleshooting

### Error: "pyvis not installed"
```bash
pip install pyvis
```

### Error: "graphviz not installed"
```bash
# Install Python package
pip install graphviz

# Install binary (macOS)
brew install graphviz

# Install binary (Linux)
sudo apt-get install graphviz
```

### Error: "No nodes found in graph data"
- Check your input JSON has `"nodes"` field
- Verify JSON is valid (use `jq . graph.json`)

### Warning: "Orthogonal edges do not currently handle edge labels"
- This is a graphviz warning for static images
- Does not affect output quality
- Labels are still rendered

## Integration with Decision Agent

The graph visualization helps understand decision agent output:

1. **Run decision agent** to get graph data:
   ```bash
   # Decision agent produces graph_data in JSON
   ```

2. **Save graph_data** to file:
   ```bash
   echo '{"nodes":[...], "edges":[...]}' > graph.json
   ```

3. **Visualize**:
   ```bash
   python visualize_graph.py --input graph.json --output graph.html --type interactive
   ```

4. **Analyze**:
   - Open `graph.html` in browser
   - Look for contradictions (red edges)
   - Identify key evidence (large nodes)
   - Understand decision reasoning

## Performance

- **Interactive HTML**: Fast for graphs up to ~100 nodes
- **Static PNG**: Fast for graphs up to ~200 nodes
- **Large graphs**: Use `--type static` for better performance

## Tips

1. **Use interactive for exploration**: Drag nodes, zoom, hover for details
2. **Use static for sharing**: PNG/SVG/PDF for reports and documentation
3. **Both types together**: Compare automatic layout (interactive) vs. hierarchical (static)
4. **Check contradictions**: Red edges indicate conflicting evidence
5. **Focus on large nodes**: Higher scores = more important evidence

## Next Steps

- Integrate with ASI:One to automatically visualize decision reasoning
- Create visualization dashboard for multiple markets
- Add time-series animation for evolving graphs
- Export graph metrics (centrality, clustering, etc.)
