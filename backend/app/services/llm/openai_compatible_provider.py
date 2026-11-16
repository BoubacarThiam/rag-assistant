"""Any OpenAI-compatible chat API (Groq, Gemini, Ollama, OpenRouter...), streamed token by token.

Many providers expose the same `/chat/completions` format: only the base URL, the key and the
model name change. This lets the project run on a free model while keeping Claude as default.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

import openai

from app.services.llm.base import ChatMessage, LLMError

logger = logging.getLogger(__name__)

MISSING_KEY_MESSAGE = "Clé API du modèle de langage absente ou invalide (LLM_API_KEY)."

# Some open models (gpt-oss) cite with full-width brackets: 【1】 instead of [1].
# Each bracket is a single character, so translating piece by piece is safe while streaming.
CITATION_BRACKETS = str.maketrans({"【": "[", "】": "]"})


class OpenAICompatibleProvider:
    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        # Local servers such as Ollama need no key, but the SDK requires a non-empty string.
        self._client = openai.AsyncOpenAI(api_key=api_key or "not-needed", base_url=base_url)
        self._model = model
        self._max_tokens = max_tokens
        # Running totals, read by the evaluation script to report token usage.
        self.input_tokens = 0
        self.output_tokens = 0

    def _request(self, system: str, messages: list[ChatMessage]) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_completion_tokens": self._max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
        }

    async def stream(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        finish_reason: str | None = None
        input_tokens = output_tokens = 0
        try:
            chunks = await self._client.chat.completions.create(**self._request(system, messages))
            async for chunk in chunks:
                if chunk.usage:  # last chunk, thanks to include_usage
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens
                for choice in chunk.choices:
                    # Only the answer: reasoning models send their thinking in another field.
                    if choice.delta.content:
                        yield choice.delta.content.translate(CITATION_BRACKETS)
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
        except openai.AuthenticationError as exc:
            raise LLMError(MISSING_KEY_MESSAGE, "llm_auth") from exc
        except openai.RateLimitError as exc:
            raise LLMError(
                "Trop de requêtes envoyées au modèle de langage (quota atteint). "
                "Réessayez dans un instant.",
                "llm_rate_limit",
            ) from exc
        except openai.APIStatusError as exc:
            logger.error("LLM API error %s: %s", exc.status_code, exc.message)
            if exc.status_code >= 500:
                raise LLMError(
                    "Le service du modèle de langage est momentanément indisponible. Réessayez.",
                    "llm_unavailable",
                ) from exc
            raise LLMError(
                "La requête a été refusée par le service du modèle de langage.", "llm_bad_request"
            ) from exc
        except openai.APIConnectionError as exc:
            raise LLMError(
                "Impossible de joindre le service du modèle de langage (LLM_BASE_URL).",
                "llm_connection",
            ) from exc
        except openai.OpenAIError as exc:
            logger.error("OpenAI SDK error: %s", exc)
            raise LLMError(
                "Le modèle de langage n'est pas configuré correctement.", "llm_config"
            ) from exc

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        logger.info(
            "LLM done: model=%s finish=%s input_tokens=%d output_tokens=%d",
            self._model,
            finish_reason,
            input_tokens,
            output_tokens,
        )
        if finish_reason == "content_filter":
            raise LLMError("Le modèle a refusé de répondre à cette demande.", "llm_refusal")
        if finish_reason == "length":
            raise LLMError(
                "La réponse a été tronquée (limite de longueur atteinte).", "llm_truncated"
            )
