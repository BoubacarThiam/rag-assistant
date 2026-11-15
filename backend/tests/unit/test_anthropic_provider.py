"""AnthropicProvider with the SDK client replaced by a stub (no network call)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest

from app.services.llm import AnthropicProvider, ChatMessage, LLMError

MESSAGES = [ChatMessage("user", "Bonjour")]


class StubStream:
    def __init__(self, texts: list[str], stop_reason: str, error: Exception | None) -> None:
        self._texts = texts
        self._stop_reason = stop_reason
        self._error = error

    async def __aenter__(self) -> "StubStream":
        if self._error:
            raise self._error
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    @property
    async def text_stream(self) -> AsyncIterator[str]:
        for text in self._texts:
            yield text

    async def get_final_message(self) -> Any:
        return SimpleNamespace(
            model="claude-opus-5-5",
            stop_reason=self._stop_reason,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


def make_provider(
    texts: list[str] | None = None,
    stop_reason: str = "end_turn",
    error: Exception | None = None,
    **kwargs: Any,
) -> tuple[AnthropicProvider, list[dict[str, Any]]]:
    provider = AnthropicProvider("claude-opus-5-5", api_key="test-key", **kwargs)
    requests: list[dict[str, Any]] = []

    def stream(**request: Any) -> StubStream:
        requests.append(request)
        return StubStream(texts or ["Bon", "jour"], stop_reason, error)

    provider._client = SimpleNamespace(
        beta=SimpleNamespace(messages=SimpleNamespace(stream=stream))
    )  # type: ignore[assignment]
    return provider, requests


def api_error(cls: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.anthropic.com"))
    return cls("boom", response=response, body=None)


async def collect(provider: AnthropicProvider) -> list[str]:
    return [text async for text in provider.stream("Système", MESSAGES)]


async def test_streams_text_and_builds_the_request() -> None:
    provider, requests = make_provider(effort="medium", max_tokens=1234)

    assert await collect(provider) == ["Bon", "jour"]
    assert requests == [
        {
            "model": "claude-opus-5-5",
            "max_tokens": 1234,
            "system": "Système",
            "messages": [{"role": "user", "content": "Bonjour"}],
            "output_config": {"effort": "medium"},
            "betas": ["server-side-fallback-2026-07-01"],
            "fallbacks": "default",
        }
    ]


async def test_optional_parameters_can_be_turned_off() -> None:
    provider, requests = make_provider(effort="", refusal_fallback=False)

    await collect(provider)

    assert requests[0].keys() == {"model", "max_tokens", "system", "messages"}


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (api_error(anthropic.AuthenticationError, 401), "llm_auth"),
        (api_error(anthropic.RateLimitError, 429), "llm_rate_limit"),
        (api_error(anthropic.InternalServerError, 529), "llm_unavailable"),
        (api_error(anthropic.BadRequestError, 400), "llm_bad_request"),
        (
            anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com")
            ),
            "llm_connection",
        ),
    ],
)
async def test_sdk_errors_become_llm_errors(error: Exception, code: str) -> None:
    provider, _ = make_provider(error=error)

    with pytest.raises(LLMError) as raised:
        await collect(provider)

    assert raised.value.code == code
    assert "boom" not in raised.value.message  # no internal detail shown to the user


@pytest.mark.parametrize(
    ("stop_reason", "code"), [("refusal", "llm_refusal"), ("max_tokens", "llm_truncated")]
)
async def test_abnormal_stop_reasons_are_reported(stop_reason: str, code: str) -> None:
    provider, _ = make_provider(stop_reason=stop_reason)

    with pytest.raises(LLMError) as raised:
        await collect(provider)

    assert raised.value.code == code


async def test_missing_credentials_give_a_clear_error() -> None:
    # Real client, no key: the SDK fails before any network call.
    provider = AnthropicProvider("claude-opus-5-5", api_key=None)
    provider._client.api_key = None
    provider._client.auth_token = None

    with pytest.raises(LLMError) as raised:
        await collect(provider)

    assert raised.value.code == "llm_auth"
