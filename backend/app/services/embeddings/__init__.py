"""Embedding providers and the factory used by the API (a FastAPI dependency)."""

from functools import lru_cache

from app.core.config import get_settings
from app.models.document import EMBEDDING_DIM
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.e5 import E5EmbeddingProvider
from app.services.embeddings.fake import FakeEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """One shared instance: the model is loaded once per process."""
    settings = get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(EMBEDDING_DIM)
    return E5EmbeddingProvider(settings.embedding_model, settings.embedding_batch_size)


__all__ = [
    "E5EmbeddingProvider",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "get_embedding_provider",
]
