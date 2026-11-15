"""LLM provider interface: the chat service only needs "stream me the answer as text pieces"."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


class LLMError(Exception):
    """The LLM call failed. `message` is safe to show to the user (French)."""

    def __init__(self, message: str, code: str = "llm_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class LLMProvider(Protocol):
    def stream(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield the answer piece by piece. Raises LLMError on failure."""
        ...
