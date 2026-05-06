"""LangGraph workflow — builds and runs the multi-agent research graph."""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentResult, ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent()
        self._analyst = AnalystAgent()
        self._writer = WriterAgent()
        self._critic = CriticAgent()
        self._settings = get_settings()

    def build(self) -> StateGraph:
        """Create a LangGraph StateGraph with nodes, edges, conditional routing, and stop condition."""

        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("analyst", self._analyst_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("critic", self._critic_node)

        # Entry point
        graph.set_entry_point("supervisor")

        # Conditional routing from supervisor
        graph.add_conditional_edges(
            "supervisor",
            self._route_decision,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        # Workers always return to supervisor
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "critic")
        graph.add_edge("critic", "supervisor")

        return graph

    def run(self, state: ResearchState) -> ResearchState:
        """Compile graph, invoke it, and convert result back to ResearchState."""

        with trace_span("multi_agent_workflow", {"query": state.request.query}):
            graph = self.build()
            compiled = graph.compile()

            # Convert state to dict for LangGraph
            state_dict = state.model_dump()

            logger.info("Starting multi-agent workflow for: %s", state.request.query)
            result = compiled.invoke(state_dict)

            # Convert back to ResearchState, preserving sources and agent_results
            raw_sources = result.get("sources", [])
            sources = []
            for s in raw_sources:
                if isinstance(s, dict):
                    sources.append(SourceDocument(**s))
                else:
                    sources.append(s)

            raw_results = result.get("agent_results", [])
            agent_results = []
            for r in raw_results:
                if isinstance(r, dict):
                    agent_results.append(AgentResult(**r))
                else:
                    agent_results.append(r)

            final_state = ResearchState(
                request=ResearchQuery(**result["request"]),
                iteration=result.get("iteration", 0),
                route_history=result.get("route_history", []),
                sources=sources,
                research_notes=result.get("research_notes"),
                analysis_notes=result.get("analysis_notes"),
                final_answer=result.get("final_answer"),
                agent_results=agent_results,
                trace=result.get("trace", []),
                errors=result.get("errors", []),
            )

            logger.info("Workflow completed: %d iterations, route=%s",
                        final_state.iteration, final_state.route_history)
            return final_state

    # --- Node wrappers (dict ↔ ResearchState) ---

    def _to_state(self, data: dict[str, Any]) -> ResearchState:
        """Convert dict to ResearchState, handling nested models."""
        request = data.get("request", {})
        if isinstance(request, dict):
            request = ResearchQuery(**request)
        return ResearchState(
            request=request,
            iteration=data.get("iteration", 0),
            route_history=data.get("route_history", []),
            sources=data.get("sources", []),
            research_notes=data.get("research_notes"),
            analysis_notes=data.get("analysis_notes"),
            final_answer=data.get("final_answer"),
            agent_results=data.get("agent_results", []),
            trace=data.get("trace", []),
            errors=data.get("errors", []),
        )

    def _supervisor_node(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._to_state(data)
        result = self._supervisor.run(state)
        return result.model_dump()

    def _researcher_node(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._to_state(data)
        result = self._researcher.run(state)
        return result.model_dump()

    def _analyst_node(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._to_state(data)
        result = self._analyst.run(state)
        return result.model_dump()

    def _writer_node(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._to_state(data)
        result = self._writer.run(state)
        return result.model_dump()

    def _critic_node(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._to_state(data)
        result = self._critic.run(state)
        return result.model_dump()

    @staticmethod
    def _route_decision(data: dict[str, Any]) -> str:
        """Extract latest route from supervisor's route_history."""
        route_history = data.get("route_history", [])
        if route_history:
            return route_history[-1]
        return "done"
