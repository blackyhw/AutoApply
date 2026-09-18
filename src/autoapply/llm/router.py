from __future__ import annotations

from autoapply.errors import LlmError, LlmRateLimitError
from autoapply.llm.base import LlmProvider, LlmRequest, LlmResponse
from autoapply.logging import get_logger

log = get_logger("llm.router")


class LlmRouter:
    """Primary provider with automatic fallback on rate limits."""

    def __init__(self, primary: LlmProvider, fallback: LlmProvider | None = None):
        self.primary = primary
        self.fallback = fallback

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        try:
            return await self.primary.complete_json(request)
        except LlmRateLimitError as exc:
            if self.fallback is None:
                raise
            log.warning(
                "primary_llm_rate_limited",
                primary=getattr(self.primary, "name", "unknown"),
                error=str(exc),
            )
            return await self.fallback.complete_json(request)
        except LlmError:
            if self.fallback is None:
                raise
            log.warning(
                "primary_llm_failed_using_fallback",
                primary=getattr(self.primary, "name", "unknown"),
            )
            return await self.fallback.complete_json(request)


def build_llm_router(*, gemini_key: str, groq_key: str, gemini_model: str, groq_model: str, allow_mock: bool = True) -> LlmRouter:
    from autoapply.llm.gemini import GeminiProvider
    from autoapply.llm.groq import GroqProvider
    from autoapply.llm.mock import MockProvider

    primary: LlmProvider
    fallback: LlmProvider | None = None
    if gemini_key:
        primary = GeminiProvider(gemini_key, gemini_model)
        if groq_key:
            fallback = GroqProvider(groq_key, groq_model)
        elif allow_mock:
            fallback = MockProvider()
    elif groq_key:
        primary = GroqProvider(groq_key, groq_model)
    elif allow_mock:
        primary = MockProvider()
    else:
        raise LlmError("No LLM provider configured (need GEMINI_API_KEY or GROQ_API_KEY)")
    return LlmRouter(primary, fallback)
