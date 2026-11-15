import math

from app.services.embeddings import FakeEmbeddingProvider


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))  # vectors are normalized


def test_vectors_are_deterministic_and_normalized() -> None:
    provider = FakeEmbeddingProvider()
    first = provider.embed_query("Les congés payés")
    assert first == provider.embed_query("Les congés payés")
    assert len(first) == provider.dimension
    assert math.isclose(math.sqrt(sum(x * x for x in first)), 1.0)


def test_texts_sharing_words_are_closer() -> None:
    provider = FakeEmbeddingProvider()
    query = provider.embed_query("congés payés")
    related, unrelated = provider.embed_documents(
        ["Les congés payés sont de 25 jours.", "La cantine ouvre à midi."]
    )
    assert cosine(query, related) > cosine(query, unrelated)


def test_empty_text_still_gives_a_valid_vector() -> None:
    assert math.isclose(sum(x * x for x in FakeEmbeddingProvider().embed_query("")), 1.0)
