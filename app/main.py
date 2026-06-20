"""Main entry point for the prediction market system"""

import json
from datetime import datetime

from app.config import Config
from app.schemas.market import Market
from app.agents.coordinator import Coordinator


def print_header(text: str, width: int = 80):
    """Print a formatted header"""
    print("\n" + "=" * width)
    print(text.center(width))
    print("=" * width + "\n")


def print_section(title: str):
    """Print a section divider"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")


def format_result_report(result: dict) -> str:
    """Format the result as a readable terminal report"""
    market = result["market"]
    compression = result["compression"]
    decision = result["decision"]

    lines = []

    # Market info
    lines.append("MARKET INFORMATION")
    lines.append("─" * 80)
    lines.append(f"Title: {market.title}")
    lines.append(f"Question: {market.question}")
    lines.append(f"Category: {market.category}")
    lines.append(f"Current YES price: {market.current_yes_price}")
    lines.append(f"Current NO price: {market.current_no_price}")
    lines.append("")

    # Compression metrics
    lines.append("COMPRESSION METRICS")
    lines.append("─" * 80)
    lines.append(f"Raw token count: {compression.raw_token_count:,}")
    lines.append(f"Compressed token count: {compression.compressed_token_count:,}")
    lines.append(f"Compression ratio: {compression.compression_ratio:.2f}x")
    lines.append(f"Tokens saved: {compression.raw_token_count - compression.compressed_token_count:,}")
    percent_saved = ((compression.raw_token_count - compression.compressed_token_count) / compression.raw_token_count * 100) if compression.raw_token_count > 0 else 0
    lines.append(f"Percent saved: {percent_saved:.1f}%")
    lines.append(f"Protected terms: {len(compression.protected_terms)}")
    lines.append(f"Chunks kept: {len(compression.kept_chunks)}")
    lines.append(f"Chunks dropped: {len(compression.dropped_chunks)}")
    lines.append("")

    # Top kept evidence
    lines.append("TOP KEPT EVIDENCE (High-Score Chunks)")
    lines.append("─" * 80)
    for i, chunk in enumerate(compression.kept_chunks[:5], 1):
        score = chunk.get('score', 0)
        text = chunk.get('text', '')
        # Truncate long text
        if len(text) > 150:
            text = text[:147] + "..."
        lines.append(f"{i}. [Score: {score:.3f}] {text}")
    lines.append("")

    # Example dropped evidence
    lines.append("EXAMPLE DROPPED EVIDENCE (Low-Score Chunks)")
    lines.append("─" * 80)
    for i, chunk in enumerate(compression.dropped_chunks[:3], 1):
        score = chunk.get('score', 0)
        text = chunk.get('text', '')
        # Truncate long text
        if len(text) > 150:
            text = text[:147] + "..."
        lines.append(f"{i}. [Score: {score:.3f}] {text}")
    lines.append("")

    # Decision
    lines.append("DECISION")
    lines.append("─" * 80)
    lines.append(f"Recommendation: {decision.recommendation}")
    lines.append(f"Confidence: {decision.confidence:.2%}")
    if decision.fair_probability is not None:
        lines.append(f"Fair probability: {decision.fair_probability:.2%}")
        if market.current_yes_price:
            edge = decision.fair_probability - market.current_yes_price
            lines.append(f"Estimated edge: {edge:+.2%}")
    lines.append("")
    lines.append(f"Reasoning: {decision.reasoning}")
    lines.append("")

    # Key evidence
    lines.append("KEY EVIDENCE:")
    for i, evidence in enumerate(decision.key_evidence, 1):
        lines.append(f"  {i}. {evidence}")
    lines.append("")

    # Missing info
    lines.append("MISSING INFORMATION:")
    for i, info in enumerate(decision.missing_info, 1):
        lines.append(f"  {i}. {info}")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point"""
    print_header("MULTI-AGENT PREDICTION MARKET RESEARCH", 80)
    print_header("WITH CONTEXT COMPRESSION", 80)

    print("This is the MVP implementation.")
    print("Only the CultureWebAgent is active. Other agents are scaffolded.")
    print("No API keys required. Running entirely locally.\n")

    # Load the market
    print_section("Loading Market Data")
    market_file = Config.get_market_file("culture_market.json")
    print(f"Loading market from: {market_file}")

    with open(market_file, 'r') as f:
        market_data = json.load(f)

    market = Market(**market_data)
    print(f"✓ Loaded market: {market.title}\n")

    # Initialize coordinator
    print_section("Initializing Coordinator")
    coordinator = Coordinator(token_budget=Config.DEFAULT_TOKEN_BUDGET)
    print(f"✓ Token budget: {Config.DEFAULT_TOKEN_BUDGET:,}")
    print("✓ All agents initialized\n")

    # Run the pipeline
    print_section("Running Research Pipeline")
    result = coordinator.run(market)

    # Print results
    print_section("RESULTS")
    report = format_result_report(result)
    print(report)

    # Save output
    print_section("Saving Output")
    output_file = Config.get_output_file("latest_result.json")

    # Convert Pydantic models to dicts for JSON serialization
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "market": market.model_dump(),
        "compression": result["compression"].model_dump(),
        "decision": result["decision"].model_dump()
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Saved full output to: {output_file}")
    print(f"\nDone! The compression middleware reduced context by {result['compression'].compression_ratio:.2f}x")
    print("while preserving decision-relevant evidence.\n")


if __name__ == "__main__":
    main()
