"""Researcher agent — collects sources and creates concise research notes."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """You are a Research Agent. Your job is to synthesize search results into clear, well-organized research notes.

Instructions:
1. Read the search results carefully.
2. Extract the most important facts, claims, and insights.
3. Organize notes by topic/theme.
4. Include source references using [Source N] format.
5. Be factual and concise — no opinions or speculation.
6. Aim for 300-500 words of notes."""


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._search = SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Implements search, source filtering, citation capture, and notes synthesis.
        """

        with trace_span("researcher_run", {"query": state.request.query}) as span:
            # Step 1: Search for sources
            logger.info("Researcher searching for: %s", state.request.query)
            sources = self._search.search(
                query=state.request.query,
                max_results=state.request.max_sources,
            )
            state.sources = sources
            span["attributes"]["num_sources"] = len(sources)

            # Step 2: Build source context for LLM
            source_context = self._format_sources(sources)

            user_prompt = (
                f"Research Query: {state.request.query}\n"
                f"Target Audience: {state.request.audience}\n\n"
                f"Search Results:\n{source_context}\n\n"
                "Please synthesize these results into comprehensive research notes."
            )

            # Step 3: Generate research notes via LLM
            try:
                response = self._llm.complete(RESEARCHER_SYSTEM_PROMPT, user_prompt)
                state.research_notes = response.content

                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.RESEARCHER,
                        content=response.content,
                        metadata={
                            "num_sources": len(sources),
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )
                span["attributes"]["notes_length"] = len(response.content)
                logger.info("Researcher generated %d chars of notes from %d sources",
                           len(response.content), len(sources))

            except Exception as exc:
                error_msg = f"Researcher LLM error: {exc}"
                logger.error(error_msg)
                state.errors.append(error_msg)
                # Fallback: use raw source snippets as notes
                state.research_notes = f"[Fallback notes from {len(sources)} sources]\n\n" + source_context

            state.add_trace_event("researcher", {
                "num_sources": len(sources),
                "notes_preview": (state.research_notes or "")[:200],
            })

        return state

    @staticmethod
    def _format_sources(sources: list) -> str:
        """Format source documents into a readable context string."""

        parts: list[str] = []
        for i, source in enumerate(sources, 1):
            parts.append(f"[Source {i}] {source.title}")
            if source.url:
                parts.append(f"  URL: {source.url}")
            parts.append(f"  Content: {source.snippet}")
            parts.append("")
        return "\n".join(parts)
