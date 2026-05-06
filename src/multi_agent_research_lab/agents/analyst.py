"""Analyst agent — turns research notes into structured insights."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """You are an Analyst Agent. Your job is to critically analyze research notes and produce structured insights.

Instructions:
1. Extract the key claims and findings from the research notes.
2. Compare different viewpoints and identify areas of consensus and disagreement.
3. Flag any claims with weak or missing evidence.
4. Identify gaps in the research that need further investigation.
5. Rate the overall strength of evidence (Strong / Moderate / Weak).
6. Organize your analysis using clear headings.

Output format:
## Key Claims
- Claim 1: ... [Evidence: Strong/Moderate/Weak]
- Claim 2: ...

## Viewpoint Comparison
...

## Evidence Gaps
...

## Overall Assessment
..."""


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Extracts key claims, compares viewpoints, and flags weak evidence.
        """

        with trace_span("analyst_run") as span:
            if not state.research_notes:
                logger.warning("Analyst called without research_notes — skipping")
                state.errors.append("Analyst: no research_notes available")
                return state

            user_prompt = (
                f"Research Query: {state.request.query}\n"
                f"Target Audience: {state.request.audience}\n\n"
                f"Research Notes:\n{state.research_notes}\n\n"
                f"Number of sources consulted: {len(state.sources)}\n\n"
                "Please analyze these research notes critically."
            )

            try:
                response = self._llm.complete(ANALYST_SYSTEM_PROMPT, user_prompt)
                state.analysis_notes = response.content

                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.ANALYST,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )
                span["attributes"]["analysis_length"] = len(response.content)
                logger.info("Analyst generated %d chars of analysis", len(response.content))

            except Exception as exc:
                error_msg = f"Analyst LLM error: {exc}"
                logger.error(error_msg)
                state.errors.append(error_msg)
                state.analysis_notes = "[Analyst fallback] Unable to generate analysis."

            state.add_trace_event("analyst", {
                "analysis_preview": (state.analysis_notes or "")[:200],
            })

        return state
