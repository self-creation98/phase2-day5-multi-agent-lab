"""Critic agent — fact-checking and quality review."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a Critic Agent. Review the final answer for accuracy and quality.

Check:
1. Are claims supported by the provided sources?
2. Citation coverage: how many key claims have source references?
3. Any potential hallucinations or unsupported statements?
4. Clarity and organization of the response.
5. Does it adequately address the original query?

Output a brief review with:
- Citation Coverage Score: X/10
- Accuracy Assessment: High/Medium/Low
- Issues Found: (list any)
- Recommendation: Approve / Needs Revision"""


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings."""

        with trace_span("critic_run") as span:
            if not state.final_answer:
                logger.warning("Critic: no final_answer to review")
                return state

            source_list = "\n".join(
                f"[Source {i}] {s.title}: {s.snippet[:100]}"
                for i, s in enumerate(state.sources, 1)
            )

            user_prompt = (
                f"Query: {state.request.query}\n\n"
                f"Final Answer:\n{state.final_answer}\n\n"
                f"Sources:\n{source_list}\n\n"
                "Review this answer."
            )

            try:
                response = self._llm.complete(CRITIC_SYSTEM_PROMPT, user_prompt)
                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.CRITIC,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )
                span["attributes"]["review_length"] = len(response.content)
                logger.info("Critic review: %d chars", len(response.content))
            except Exception as exc:
                logger.error("Critic error: %s", exc)
                state.errors.append(f"Critic error: {exc}")

            state.add_trace_event("critic", {"reviewed": True})
        return state
