"""Tests for implemented agents (post-TODO completion)."""

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_to_researcher_when_no_notes() -> None:
    """Supervisor should route to researcher when there are no research notes."""
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "researcher"
    assert result.iteration == 1


def test_supervisor_routes_to_done_at_max_iterations() -> None:
    """Supervisor should force 'done' when max iterations is reached."""
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.iteration = 100  # exceed max
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "done"
