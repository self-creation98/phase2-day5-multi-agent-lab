"""Search client abstraction for ResearcherAgent."""

import logging

from tavily import TavilyClient

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Tavily-based search client with fallback to mock data."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.tavily_api_key
        if self._api_key:
            self._client = TavilyClient(api_key=self._api_key)
        else:
            self._client = None
            logger.warning("TAVILY_API_KEY not set — using mock search results")

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query using Tavily or mock fallback."""

        if self._client is None:
            return self._mock_search(query, max_results)

        logger.info("Tavily search: query=%r, max_results=%d", query, max_results)

        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
            )

            documents: list[SourceDocument] = []
            for result in response.get("results", []):
                documents.append(
                    SourceDocument(
                        title=result.get("title", "Untitled"),
                        url=result.get("url"),
                        snippet=result.get("content", ""),
                        metadata={"score": result.get("score", 0.0)},
                    )
                )

            logger.info("Tavily returned %d results", len(documents))
            return documents

        except Exception as exc:
            logger.error("Tavily search failed: %s — falling back to mock", exc)
            return self._mock_search(query, max_results)

    @staticmethod
    def _mock_search(query: str, max_results: int = 5) -> list[SourceDocument]:
        """Return mock search results for development/testing."""

        mock_sources = [
            SourceDocument(
                title="Multi-Agent Systems: A Survey",
                url="https://arxiv.org/abs/2402.01680",
                snippet="Multi-agent systems decompose complex tasks into specialized sub-tasks "
                        "handled by different agents. Key patterns include supervisor-worker, "
                        "peer-to-peer, and hierarchical architectures.",
                metadata={"source": "mock"},
            ),
            SourceDocument(
                title="Building Effective AI Agents - Anthropic",
                url="https://www.anthropic.com/engineering/building-effective-agents",
                snippet="Start with the simplest solution. Agents add complexity. Use workflows "
                        "for predictable tasks and agents for open-ended tasks requiring autonomy.",
                metadata={"source": "mock"},
            ),
            SourceDocument(
                title="LangGraph: Multi-Actor Orchestration Framework",
                url="https://langchain-ai.github.io/langgraph/",
                snippet="LangGraph provides a framework for building stateful, multi-agent "
                        "applications using graph-based workflows with nodes, edges, and "
                        "conditional routing.",
                metadata={"source": "mock"},
            ),
        ]
        return mock_sources[:max_results]
