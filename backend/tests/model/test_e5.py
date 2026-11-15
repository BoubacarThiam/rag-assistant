"""Checks with the REAL embedding model (downloads ~1 GB the first time).

Skipped by default; run with: RUN_MODEL_TESTS=1 uv run pytest tests/model
"""

import math
import os

import pytest

from app.core.config import get_settings
from app.models import EMBEDDING_DIM
from app.services.embeddings import E5EmbeddingProvider

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "1", reason="set RUN_MODEL_TESTS=1"),
]


@pytest.fixture(scope="module")
def provider() -> E5EmbeddingProvider:
    return E5EmbeddingProvider(get_settings().embedding_model)


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_dimension_matches_database_column(provider: E5EmbeddingProvider) -> None:
    assert provider.dimension == EMBEDDING_DIM


def test_vectors_are_normalized(provider: E5EmbeddingProvider) -> None:
    (vector,) = provider.embed_documents(["Bonjour"])
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, rel_tol=1e-4)


def test_semantic_similarity_beyond_shared_words(provider: E5EmbeddingProvider) -> None:
    query = provider.embed_query("Combien de jours de vacances ai-je par an ?")
    related, unrelated = provider.embed_documents(
        [
            "Chaque salarié bénéficie de 25 jours de congés payés annuels.",
            "La cantine de l'entreprise ouvre à midi.",
        ]
    )
    assert cosine(query, related) > cosine(query, unrelated)


def test_token_count_uses_the_model_tokenizer(provider: E5EmbeddingProvider) -> None:
    # Subword tokenizer: more tokens than words for French text.
    text = "L'anticonstitutionnalité des dispositions réglementaires."
    assert provider.count_tokens(text) > len(text.split())
