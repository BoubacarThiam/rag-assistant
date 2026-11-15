"""LLM providers and the factory used by the API (a FastAPI dependency)."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.llm.fake import FakeLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    api_key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
    return AnthropicProvider(
        settings.llm_model,
        api_key=api_key,
        max_tokens=settings.llm_max_tokens,
        effort=settings.llm_effort,
        refusal_fallback=settings.llm_refusal_fallback,
    )


__all__ = [
    "AnthropicProvider",
    "ChatMessage",
    "FakeLLMProvider",
    "LLMError",
    "LLMProvider",
    "get_llm_provider",
]
