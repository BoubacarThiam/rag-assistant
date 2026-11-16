"""OpenAICompatibleProvider with the SDK client replaced by a stub (no network call)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.core.config import Settings
from app.services.llm import ChatMessage, LLMError, OpenAICompatibleProvider

MESSAGES = [ChatMessage("user", "Bonjour")]


def chunk(
    content: str | None = None,
    *,
    reasoning: str | None = None,
    finish_reason: str | None = None,
    usage: tuple[int, int] | None = None,
) -> Any:
    choices = []
    if content is not None or reasoning is not None or finish_reason is not None:
        delta = SimpleNamespace(content=content, reasoning=reasoning)
        choices.append(SimpleNamespace(delta=delta, finish_reason=finish_reason))
    counts = SimpleNamespace(prompt_tokens=usage[0], completion_tokens=usage[1]) if usage else None
    return SimpleNamespace(choices=choices, usage=counts)


DEFAULT_CHUNKS = [
    chunk(reasoning="The user greets."),  # thinking of a reasoning model: must not be shown
    chunk("Bon"),
    chunk("jour"),
    chunk(finish_reason="stop"),
    chunk(usage=(12, 7)),
]


def make_provider(
    chunks: list[Any] | None = None, error: Exception | None = None
) -> tuple[OpenAICompatibleProvider, list[dict[str, Any]]]:
    provider = OpenAICompatibleProvider(
        "openai/gpt-oss-120b", base_url="https://example.test/v1", api_key="k", max_tokens=1000
    )
    requests: list[dict[str, Any]] = []

    async def create(**request: Any) -> AsyncIterator[Any]:
        requests.append(request)
        if error:
            raise error

        async def gen() -> AsyncIterator[Any]:
            for c in DEFAULT_CHUNKS if chunks is None else chunks:
                yield c

        return gen()

    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )  # type: ignore[assignment]
    return provider, requests


async def collect(provider: OpenAICompatibleProvider) -> list[str]:
    return [piece async for piece in provider.stream("Consigne", MESSAGES)]


async def test_streams_only_the_answer_and_counts_tokens() -> None:
    provider, requests = make_provider()
    assert await collect(provider) == ["Bon", "jour"]
    assert (provider.input_tokens, provider.output_tokens) == (12, 7)
    request = requests[0]
    assert request["model"] == "openai/gpt-oss-120b"
    assert request["max_completion_tokens"] == 1000
    assert request["stream"] is True
    # The system prompt becomes the first message in the OpenAI format.
    assert request["messages"] == [
        {"role": "system", "content": "Consigne"},
        {"role": "user", "content": "Bonjour"},
    ]


async def test_full_width_citation_brackets_are_normalized() -> None:
    provider, _ = make_provider([chunk("27 jours【"), chunk("1】."), chunk(finish_reason="stop")])
    assert "".join(await collect(provider)) == "27 jours[1]."


@pytest.mark.parametrize(
    ("finish_reason", "code"), [("length", "llm_truncated"), ("content_filter", "llm_refusal")]
)
async def test_bad_finish_reason_raises(finish_reason: str, code: str) -> None:
    provider, _ = make_provider([chunk("Début"), chunk(finish_reason=finish_reason)])
    with pytest.raises(LLMError) as info:
        await collect(provider)
    assert info.value.code == code


def status_error(cls: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return cls("boom", response=httpx.Response(status, request=request), body=None)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (status_error(openai.AuthenticationError, 401), "llm_auth"),
        (status_error(openai.RateLimitError, 429), "llm_rate_limit"),
        (status_error(openai.InternalServerError, 503), "llm_unavailable"),
        (status_error(openai.BadRequestError, 400), "llm_bad_request"),
        (
            openai.APIConnectionError(request=httpx.Request("POST", "https://example.test")),
            "llm_connection",
        ),
    ],
)
async def test_sdk_errors_become_llm_errors(error: Exception, code: str) -> None:
    provider, _ = make_provider(error=error)
    with pytest.raises(LLMError) as info:
        await collect(provider)
    assert info.value.code == code


def test_settings_select_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import llm

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        llm_provider="openai_compatible",
        llm_model="openai/gpt-oss-120b",
        llm_api_key="k",  # type: ignore[arg-type]
    )
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm.get_llm_provider.cache_clear()
    try:
        assert isinstance(llm.get_llm_provider(), OpenAICompatibleProvider)
    finally:
        llm.get_llm_provider.cache_clear()
