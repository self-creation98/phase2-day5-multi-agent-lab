# Benchmark Report: Single-Agent vs Multi-Agent

**Generated**: 2026-05-06 05:25 UTC

## Summary Table

| Run | Latency (s) | Cost (USD) | Quality (0-10) | Notes |
|---|---:|---:|---:|---|
| baseline_q1 | 12.83 | $0.0005 | 6.0 | iterations=0 | sources=0 | errors=0 | citation_coverage=0% |
| multi_q1 | 40.67 | $0.0022 | 10.0 | iterations=4 | sources=5 | errors=0 | citation_coverage=100% | route=researcher -> analyst -> writer -> done |
| baseline_q2 | 10.55 | $0.0005 | 6.0 | iterations=0 | sources=0 | errors=0 | citation_coverage=0% |
| multi_q2 | 36.49 | $0.0021 | 10.0 | iterations=4 | sources=5 | errors=0 | citation_coverage=100% | route=researcher -> analyst -> writer -> done |
| baseline_q3 | 9.93 | $0.0005 | 6.0 | iterations=0 | sources=0 | errors=0 | citation_coverage=0% |
| multi_q3 | 40.55 | $0.0022 | 10.0 | iterations=4 | sources=5 | errors=0 | citation_coverage=100% | route=researcher -> analyst -> writer -> done |


## Comparison Analysis

- **Latency**: Multi-agent is 3.2× slower than baseline
- **Cost**: Multi-agent costs 4.8× more
- **Quality**: Multi-agent scores +4.0 points higher

## Failure Modes & Mitigations

| Failure Mode | Impact | Mitigation |
|---|---|---|
| LLM timeout/rate limit | Agent hangs | Tenacity retry with exponential backoff |
| Supervisor infinite loop | Cost blowup | `max_iterations` guard (default: 6) |
| Search API failure | No sources | Mock fallback with curated documents |
| Hallucinated citations | Low trust | Critic agent validates against sources |
| Token limit exceeded | Truncated output | Chunked context + summarization |

## Recommendations

1. **Use multi-agent** for complex research queries needing multiple perspectives.
2. **Use single-agent** for simple factual questions where latency matters.
3. **Add Critic agent** when accuracy is critical (e.g., medical, legal domains).
4. **Monitor costs** — multi-agent uses 3-5x more tokens than single-agent.

## LangSmith Traces

All traces are available in the LangSmith project: **multi-agent-research-lab**

- Dashboard: https://smith.langchain.com
- Project: `multi-agent-research-lab`
- Total traces: 7 (all successful, 0% error rate)
- P50 latency: 36.18s | P99 latency: 39.64s

### LangSmith Dashboard
![LangSmith Dashboard](screenshots/langsmith_dashboard.png)

### Trace List
![LangSmith Traces](screenshots/langsmith_traces.png)

## Architecture

```
User Query
   |
   v
Supervisor / Router (LLM-based routing with deterministic fallback)
   |------> Researcher Agent  -> search (Tavily) + LLM notes -> research_notes
   |------> Analyst Agent     -> LLM analysis -> analysis_notes
   |------> Writer Agent      -> LLM synthesis -> final_answer
   |            |
   |            v
   |        Critic Agent      -> fact-check + citation review
   |
   v
Trace (LangSmith) + Benchmark Report
```

## Exit Ticket

### 1. When should you use multi-agent?

Multi-agent is beneficial when:
- The task requires **multiple specialized skills** (search, analysis, writing)
- **Quality matters more than speed** — multi-agent scored 10.0 vs 6.0 for baseline
- Tasks need **real-time information** from external sources (web search)
- **Citation coverage** is important — multi-agent achieved 100% vs 0%
- The problem involves **complex reasoning** that benefits from structured decomposition

### 2. When should you NOT use multi-agent?

Multi-agent is unnecessary when:
- The query is **simple and factual** — a single LLM call is sufficient
- **Latency is critical** — multi-agent is 3-4x slower (~37s vs ~11s)
- **Cost constraints** are tight — multi-agent costs 4-5x more per query
- The task doesn't benefit from **task decomposition**
- You need **predictable execution time** — multi-agent has higher variance

