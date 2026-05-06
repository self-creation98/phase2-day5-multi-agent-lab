"""Benchmark report rendering with rich analysis."""

from datetime import datetime, timezone

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to a comprehensive markdown report."""

    lines = [
        "# Benchmark Report: Single-Agent vs Multi-Agent",
        "",
        f"**Generated**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary Table",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality (0-10) | Notes |",
        "|---|---:|---:|---:|---|",
    ]

    for item in metrics:
        cost = "—" if item.estimated_cost_usd is None else f"${item.estimated_cost_usd:.4f}"
        quality = "—" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |")

    lines.append("")

    # Analysis section
    if len(metrics) >= 2:
        baseline = metrics[0]
        multi = metrics[1]
        lines.extend(_comparison_analysis(baseline, multi))

    # Failure modes
    lines.extend([
        "",
        "## Failure Modes & Mitigations",
        "",
        "| Failure Mode | Impact | Mitigation |",
        "|---|---|---|",
        "| LLM timeout/rate limit | Agent hangs | Tenacity retry with exponential backoff |",
        "| Supervisor infinite loop | Cost blowup | `max_iterations` guard (default: 6) |",
        "| Search API failure | No sources | Mock fallback with curated documents |",
        "| Hallucinated citations | Low trust | Critic agent validates against sources |",
        "| Token limit exceeded | Truncated output | Chunked context + summarization |",
        "",
        "## Recommendations",
        "",
        "1. **Use multi-agent** for complex research queries needing multiple perspectives.",
        "2. **Use single-agent** for simple factual questions where latency matters.",
        "3. **Add Critic agent** when accuracy is critical (e.g., medical, legal domains).",
        "4. **Monitor costs** — multi-agent uses 3-5× more tokens than single-agent.",
        "",
    ])

    return "\n".join(lines)


def _comparison_analysis(baseline: BenchmarkMetrics, multi: BenchmarkMetrics) -> list[str]:
    """Generate comparison analysis between baseline and multi-agent."""

    lines = [
        "",
        "## Comparison Analysis",
        "",
    ]

    # Latency
    latency_ratio = multi.latency_seconds / baseline.latency_seconds if baseline.latency_seconds > 0 else 0
    lines.append(f"- **Latency**: Multi-agent is {latency_ratio:.1f}× {'slower' if latency_ratio > 1 else 'faster'} than baseline")

    # Cost
    if baseline.estimated_cost_usd and multi.estimated_cost_usd:
        cost_ratio = multi.estimated_cost_usd / baseline.estimated_cost_usd
        lines.append(f"- **Cost**: Multi-agent costs {cost_ratio:.1f}× more")

    # Quality
    if baseline.quality_score is not None and multi.quality_score is not None:
        quality_diff = multi.quality_score - baseline.quality_score
        lines.append(f"- **Quality**: Multi-agent scores {'+' if quality_diff >= 0 else ''}{quality_diff:.1f} points {'higher' if quality_diff >= 0 else 'lower'}")

    return lines
