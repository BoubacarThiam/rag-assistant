"""LLM providers and the factory used by the API (a FastAPI dependency)."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.llm.fake import FakeLLMProvider
from app.services.llm.openai_compatible_provider import OpenAICompatibleProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "openai_compatible":
        key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
        return OpenAICompatibleProvider(
            settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=key,
            max_tokens=settings.llm_max_tokens,
        )
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
    "OpenAICompatibleProvider",
    "get_llm_provider",
]
