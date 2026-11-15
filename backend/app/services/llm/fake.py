"""Scripted LLM for tests: no network, no cost, fully predictable."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.services.llm.base import ChatMessage, LLMError


@dataclass
class FakeLLMCall:
    system: str
    messages: list[ChatMessage]


@dataclass
class FakeLLMProvider:
    chunks: list[str] = field(default_factory=lambda: ["Réponse ", "de test [1]."])
    error: LLMError | None = None  # raised after the chunks have been sent
    calls: list[FakeLLMCall] = field(default_factory=list)

    async def stream(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        self.calls.append(FakeLLMCall(system, list(messages)))
        for chunk in self.chunks:
            yield chunk
        if self.error:
            raise self.error
