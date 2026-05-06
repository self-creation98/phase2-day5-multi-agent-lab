"""Tracing hooks with LangSmith integration.

Supports LangSmith for production tracing and falls back to simple JSON traces.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Configure LangSmith tracing if API key is available."""

    from multi_agent_research_lab.core.config import get_settings
    settings = get_settings()

    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info("LangSmith tracing enabled - project: %s", settings.langsmith_project)
    else:
        logger.info("LangSmith not configured - using local trace spans only")


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Span context with timing and structured logging."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    logger.info("[SPAN START] %s | attrs=%s", name, attributes or {})
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
        logger.info("[SPAN END] %s | duration=%.3fs | attrs=%s",
                     name, span["duration_seconds"], span["attributes"])
