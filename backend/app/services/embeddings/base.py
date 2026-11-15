"""Embedding provider interface.

An *embedding* turns a text into a vector of numbers; texts with close meanings get close vectors.
The rest of the app only knows this interface, so the model can be swapped (local model, API,
fake for tests) without touching ingestion or retrieval code.

Methods are synchronous because computing embeddings is CPU-bound: callers run them in a
thread (`asyncio.to_thread`) so the event loop stays free.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        """Size of the vectors produced."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Vectors for passages to store (normalized: length 1)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Vector for a user question (normalized: length 1)."""
        ...

    def count_tokens(self, text: str) -> int:
        """Number of tokens the model sees for this text (used to size chunks)."""
        ...
