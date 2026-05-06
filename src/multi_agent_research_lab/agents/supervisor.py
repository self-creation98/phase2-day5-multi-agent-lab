"""Supervisor / router — decides which worker should run next and when to stop."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

ROUTING_SYSTEM_PROMPT = """You are a Supervisor agent that routes research tasks to specialized workers.

Available workers:
- researcher: Searches the web and creates research notes with citations.
- analyst: Analyzes research notes, extracts key claims, compares viewpoints.
- writer: Synthesizes a final answer from research and analysis notes.
- done: Stop the workflow when a quality final answer is ready.

Rules:
1. If there are NO research_notes yet, route to "researcher".
2. If there ARE research_notes but NO analysis_notes, route to "analyst".
3. If there ARE both research_notes AND analysis_notes but NO final_answer, route to "writer".
4. If there IS a final_answer, route to "done".
5. Never route to the same worker twice in a row unless necessary.

Respond with ONLY one word: researcher, analyst, writer, or done."""


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._settings = get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        Implements routing policy with max iterations guard and LLM-based decision making.
        """

        with trace_span("supervisor_routing", {"iteration": state.iteration}) as span:
            # Guard: max iterations
            if state.iteration >= self._settings.max_iterations:
                logger.warning("Max iterations (%d) reached — forcing done", self._settings.max_iterations)
                state.record_route("done")
                span["attributes"]["route"] = "done"
                span["attributes"]["reason"] = "max_iterations"
                return state

            # Build context for LLM routing decision
            user_prompt = self._build_routing_context(state)

            try:
                response = self._llm.complete(ROUTING_SYSTEM_PROMPT, user_prompt)
                route = response.content.strip().lower()

                # Validate route
                valid_routes = {"researcher", "analyst", "writer", "done"}
                if route not in valid_routes:
                    logger.warning("Invalid route %r — using deterministic fallback", route)
                    route = self._deterministic_route(state)

            except Exception as exc:
                logger.error("LLM routing failed: %s — using deterministic fallback", exc)
                state.errors.append(f"Supervisor LLM error: {exc}")
                route = self._deterministic_route(state)

            logger.info("Supervisor route decision: %s (iteration %d)", route, state.iteration)
            state.record_route(route)

            state.agent_results.append(
                AgentResult(
                    agent=AgentName.SUPERVISOR,
                    content=f"Routed to: {route}",
                    metadata={"iteration": state.iteration, "route": route},
                )
            )
            state.add_trace_event("supervisor", {"route": route, "iteration": state.iteration})

            span["attributes"]["route"] = route

        return state

    def _build_routing_context(self, state: ResearchState) -> str:
        """Build a summary of current state for the LLM router."""

        parts = [f"Query: {state.request.query}"]
        parts.append(f"Iteration: {state.iteration}/{self._settings.max_iterations}")
        parts.append(f"Route history: {state.route_history}")
        parts.append(f"Has research_notes: {state.research_notes is not None}")
        parts.append(f"Has analysis_notes: {state.analysis_notes is not None}")
        parts.append(f"Has final_answer: {state.final_answer is not None}")
        parts.append(f"Number of sources: {len(state.sources)}")
        if state.errors:
            parts.append(f"Errors: {state.errors[-3:]}")
        return "\n".join(parts)

    @staticmethod
    def _deterministic_route(state: ResearchState) -> str:
        """Fallback routing without LLM — follows a fixed sequence."""

        if state.research_notes is None:
            return "researcher"
        if state.analysis_notes is None:
            return "analyst"
        if state.final_answer is None:
            return "writer"
        return "done"
