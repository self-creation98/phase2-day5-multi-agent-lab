"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import logging
from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (gpt-4o-mini, May 2025)
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client with retry, timeout, and cost tracking."""

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.openai_model
        self._client = OpenAI(api_key=settings.openai_api_key, timeout=settings.timeout_seconds)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with token usage and cost tracking."""

        logger.info("LLM call: model=%s, system_len=%d, user_len=%d",
                     self._model, len(system_prompt), len(user_prompt))

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None

        # Estimate cost
        cost_usd: float | None = None
        if input_tokens is not None and output_tokens is not None:
            price_in, price_out = _PRICING.get(self._model, (0.15, 0.60))
            cost_usd = (input_tokens * price_in + output_tokens * price_out) / 1_000_000

        logger.info("LLM response: tokens_in=%s, tokens_out=%s, cost=$%s",
                     input_tokens, output_tokens, f"{cost_usd:.6f}" if cost_usd else "N/A")

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
