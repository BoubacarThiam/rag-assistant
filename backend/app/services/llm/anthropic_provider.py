"""Claude via the official Anthropic SDK, streamed token by token."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.services.llm.base import ChatMessage, LLMError

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MISSING_KEY_MESSAGE = "Clé API Anthropic absente ou invalide (ANTHROPIC_API_KEY)."


class AnthropicProvider:
    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        max_tokens: int = 64000,
        effort: str = "",
        refusal_fallback: bool = True,
    ) -> None:
        # Without an explicit key, the SDK resolves credentials from the environment.
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._effort = effort
        self._refusal_fallback = refusal_fallback

    def _request(self, system: str, messages: list[ChatMessage]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if self._effort:
            request["output_config"] = {"effort": self._effort}
        if self._refusal_fallback:
            # On a safety decline, the API re-runs the request on a fallback model in the same call.
            request["betas"] = [FALLBACK_BETA]
            request["fallbacks"] = "default"
        return request

    async def stream(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        try:
            async with self._client.beta.messages.stream(**self._request(system, messages)) as s:
                async for text in s.text_stream:
                    yield text
                final = await s.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise LLMError(MISSING_KEY_MESSAGE, "llm_auth") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(
                "Trop de requêtes envoyées à Claude. Réessayez dans un instant.", "llm_rate_limit"
            ) from exc
        except anthropic.APIStatusError as exc:
            logger.error("Claude API error %s: %s", exc.status_code, exc.message)
            if exc.status_code >= 500:
                raise LLMError(
                    "Le service Claude est momentanément indisponible. Réessayez.",
                    "llm_unavailable",
                ) from exc
            raise LLMError("La requête a été refusée par l'API Claude.", "llm_bad_request") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Impossible de joindre l'API Claude.", "llm_connection") from exc
        except anthropic.AnthropicError as exc:
            logger.error("Anthropic SDK error: %s", exc)
            raise LLMError(
                "Le service Claude n'est pas configuré correctement.", "llm_config"
            ) from exc
        except TypeError as exc:
            # The SDK raises a bare TypeError when no credentials are configured at all.
            if "authentication" not in str(exc).lower():
                raise
            raise LLMError(MISSING_KEY_MESSAGE, "llm_auth") from exc

        logger.info(
            "LLM done: model=%s stop=%s input_tokens=%d output_tokens=%d",
            final.model,
            final.stop_reason,
            final.usage.input_tokens,
            final.usage.output_tokens,
        )
        if final.stop_reason == "refusal":
            raise LLMError("Claude a refusé de répondre à cette demande.", "llm_refusal")
        if final.stop_reason == "max_tokens":
            raise LLMError(
                "La réponse a été tronquée (limite de longueur atteinte).", "llm_truncated"
            )
