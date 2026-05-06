"""Writer agent — produces final answer from research and analysis notes."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = """You are a Writer Agent. Synthesize research notes and analysis into a clear, well-structured final answer.

Instructions:
1. Write a comprehensive response addressing the original query.
2. Incorporate insights from both research notes and analysis.
3. Include citations using [Source N] format.
4. Structure with clear headings and paragraphs.
5. Write for the specified target audience.
6. Aim for 400-600 words.
7. End with a brief conclusion."""


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer` with citations."""

        with trace_span("writer_run") as span:
            source_list = "\n".join(
                f"[Source {i}] {s.title} — {s.url or 'N/A'}"
                for i, s in enumerate(state.sources, 1)
            )

            user_prompt = (
                f"Query: {state.request.query}\n"
                f"Audience: {state.request.audience}\n\n"
                f"--- Research Notes ---\n{state.research_notes or 'N/A'}\n\n"
                f"--- Analysis ---\n{state.analysis_notes or 'N/A'}\n\n"
                f"--- Sources ---\n{source_list}\n\n"
                "Write a comprehensive final answer."
            )

            try:
                response = self._llm.complete(WRITER_SYSTEM_PROMPT, user_prompt)
                state.final_answer = response.content
                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.WRITER,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                            "word_count": len(response.content.split()),
                        },
                    )
                )
                span["attributes"]["word_count"] = len(response.content.split())
                logger.info("Writer: %d words", len(response.content.split()))
            except Exception as exc:
                logger.error("Writer LLM error: %s", exc)
                state.errors.append(f"Writer error: {exc}")
                state.final_answer = f"[Fallback] {(state.research_notes or '')[:500]}"

            state.add_trace_event("writer", {"word_count": len((state.final_answer or "").split())})
        return state
