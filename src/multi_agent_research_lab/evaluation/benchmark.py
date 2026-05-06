"""Benchmark for single-agent vs multi-agent comparison."""

import logging
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

Runner = Callable[[str], ResearchState]


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, cost, quality, and citation coverage."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    # Calculate total cost from agent results
    total_cost = sum(
        r.metadata.get("cost_usd", 0) or 0
        for r in state.agent_results
    )

    # Calculate citation coverage
    citation_score = _compute_citation_coverage(state)

    # Quality scoring heuristic
    quality = _compute_quality_score(state)

    notes_parts = []
    notes_parts.append(f"iterations={state.iteration}")
    notes_parts.append(f"sources={len(state.sources)}")
    notes_parts.append(f"errors={len(state.errors)}")
    notes_parts.append(f"citation_coverage={citation_score:.0%}")
    if state.route_history:
        notes_parts.append(f"route={' -> '.join(state.route_history)}")

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=total_cost if total_cost > 0 else None,
        quality_score=quality,
        notes=" | ".join(notes_parts),
    )

    logger.info("Benchmark [%s]: latency=%.2fs, cost=$%.6f, quality=%.1f",
                run_name, latency, total_cost, quality or 0)
    return state, metrics


def _compute_citation_coverage(state: ResearchState) -> float:
    """Estimate citation coverage in the final answer."""

    if not state.final_answer or not state.sources:
        return 0.0

    answer = state.final_answer.lower()
    cited = sum(1 for i in range(1, len(state.sources) + 1) if f"[source {i}]" in answer)
    return cited / len(state.sources) if state.sources else 0.0


def _compute_quality_score(state: ResearchState) -> float:
    """Heuristic quality score (0-10) based on output completeness."""

    score = 0.0

    # Has final answer? (3 points)
    if state.final_answer:
        score += 3.0
        word_count = len(state.final_answer.split())
        if word_count >= 200:
            score += 1.0
        if word_count >= 400:
            score += 1.0

    # Has research notes? (2 points)
    if state.research_notes:
        score += 2.0

    # Has analysis? (1 point)
    if state.analysis_notes:
        score += 1.0

    # Has sources? (1 point)
    if state.sources:
        score += 1.0

    # No errors? (1 point)
    if not state.errors:
        score += 1.0

    return min(score, 10.0)
