"""Command-line entrypoint for the multi-agent research lab."""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing()


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline with real LLM call."""

    _init()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)

    console.print("[bold cyan]Running single-agent baseline...[/]")

    llm = LLMClient()
    system_prompt = (
        "You are a research assistant. Answer the following query comprehensively "
        "with clear structure, evidence, and citations where possible. "
        "Aim for 400-600 words."
    )
    response = llm.complete(system_prompt, query)
    state.final_answer = response.content

    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline", border_style="green"))
    console.print(f"\n[dim]Tokens: {response.input_tokens} in / {response.output_tokens} out | "
                  f"Cost: ${response.cost_usd:.6f}[/]")


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()

    console.print("[bold cyan]Running multi-agent workflow...[/]")
    result = workflow.run(state)

    console.print(Panel.fit(result.final_answer or "No answer generated", title="Multi-Agent Result", border_style="green"))
    console.print(f"\n[dim]Iterations: {result.iteration} | Route: {' -> '.join(result.route_history)}[/]")
    if result.errors:
        console.print(f"[yellow]Errors: {result.errors}[/]")


@app.command()
def benchmark() -> None:
    """Run benchmark comparing single-agent vs multi-agent on standard queries."""

    _init()
    settings = get_settings()

    queries = [
        "Research GraphRAG state-of-the-art and write a 500-word summary",
        "Compare single-agent and multi-agent workflows for customer support",
        "Summarize production guardrails for LLM agents",
    ]

    all_metrics = []

    for i, query in enumerate(queries, 1):
        console.print(f"\n[bold]Query {i}/{len(queries)}:[/] {query}")
        console.print("[dim]─" * 60 + "[/]")

        # Single-agent baseline
        console.print("  [cyan]Running baseline...[/]")

        def baseline_runner(q: str) -> ResearchState:
            llm = LLMClient()
            req = ResearchQuery(query=q)
            st = ResearchState(request=req)
            resp = llm.complete(
                "You are a research assistant. Answer comprehensively in 400-600 words.", q
            )
            st.final_answer = resp.content
            from multi_agent_research_lab.core.schemas import AgentName, AgentResult
            st.agent_results.append(AgentResult(
                agent=AgentName.WRITER, content=resp.content,
                metadata={"cost_usd": resp.cost_usd, "input_tokens": resp.input_tokens,
                          "output_tokens": resp.output_tokens}
            ))
            return st

        _, baseline_metrics = run_benchmark(f"baseline_q{i}", query, baseline_runner)
        all_metrics.append(baseline_metrics)

        # Multi-agent
        console.print("  [cyan]Running multi-agent...[/]")

        def multi_runner(q: str) -> ResearchState:
            wf = MultiAgentWorkflow()
            st = ResearchState(request=ResearchQuery(query=q))
            return wf.run(st)

        _, multi_metrics = run_benchmark(f"multi_q{i}", query, multi_runner)
        all_metrics.append(multi_metrics)

    # Render report
    report = render_markdown_report(all_metrics)

    # Save report
    report_path = Path("reports/benchmark_report.md")
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    console.print(f"\n[bold green]Report saved to {report_path}[/]")

    # Print summary table
    table = Table(title="Benchmark Summary")
    table.add_column("Run", style="cyan")
    table.add_column("Latency", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Quality", justify="right")

    for m in all_metrics:
        cost = "—" if m.estimated_cost_usd is None else f"${m.estimated_cost_usd:.4f}"
        quality = "—" if m.quality_score is None else f"{m.quality_score:.1f}"
        table.add_row(m.run_name, f"{m.latency_seconds:.2f}s", cost, quality)

    console.print(table)


if __name__ == "__main__":
    app()
