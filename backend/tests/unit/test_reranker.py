import uuid
from typing import Any

import pytest

from app.core.config import Settings
from app.services import retrieval
from app.services.embeddings import FakeEmbeddingProvider
from app.services.retrieval import SearchHit, rerank, search
from app.services.retrieval.reranker import FakeReranker, get_reranker
from tests.helpers import make_hit

HITS = [
    make_hit("La cantine ouvre à midi."),
    make_hit("Le télétravail est possible trois jours par semaine."),
    make_hit("Chaque salarié a droit à 25 jours de congés payés."),
]


class ScriptedReranker:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str]) -> list[float]:
        self.calls.append((query, passages))
        return self.scores[: len(passages)]


def test_rerank_reorders_by_score_and_keeps_the_best_k() -> None:
    result = rerank(ScriptedReranker([0.1, 0.5, 0.9]), "congés ?", HITS, k=2)

    assert [h.content for h in result] == [HITS[2].content, HITS[1].content]
    assert [h.score for h in result] == [0.9, 0.5]
    assert result[0].chunk_id == HITS[2].chunk_id  # everything but the score is preserved


def test_rerank_ties_keep_the_search_order() -> None:
    result = rerank(ScriptedReranker([0.5, 0.5, 0.5]), "q", HITS, k=3)
    assert [h.chunk_id for h in result] == [h.chunk_id for h in HITS]


def test_rerank_with_no_hits() -> None:
    assert rerank(ScriptedReranker([]), "q", [], k=5) == []


def test_fake_reranker_prefers_passages_sharing_the_query_words() -> None:
    scores = FakeReranker().score("jours de congés payés", [h.content for h in HITS])
    assert scores[2] > scores[1] > scores[0]


def test_reranker_is_off_by_default() -> None:
    get_reranker.cache_clear()
    assert get_reranker() is None


async def test_search_fetches_more_candidates_then_reranks(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[int] = []

    async def fake_vector_search(
        _session: Any, _embedding: Any, k: int, _ids: Any
    ) -> list[SearchHit]:
        requested.append(k)
        return HITS

    monkeypatch.setattr(retrieval, "vector_search", fake_vector_search)
    settings = Settings(_env_file=None, rerank_candidates=20)  # type: ignore[call-arg]
    reranker = ScriptedReranker([0.1, 0.2, 0.9])

    hits = await search(
        None,
        FakeEmbeddingProvider(),
        settings,
        "congés ?",
        k=1,
        mode="vector",
        reranker=reranker,  # type: ignore[arg-type]
    )

    assert requested == [20]  # candidates, not k
    assert [h.content for h in hits] == [HITS[2].content]
    assert reranker.calls[0][0] == "congés ?"


async def test_search_without_reranker_asks_for_exactly_k(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[int] = []

    async def fake_vector_search(
        _session: Any, _embedding: Any, k: int, _ids: Any
    ) -> list[SearchHit]:
        requested.append(k)
        return HITS[:k]

    monkeypatch.setattr(retrieval, "vector_search", fake_vector_search)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    hits = await search(None, FakeEmbeddingProvider(), settings, "q", k=2, mode="vector")  # type: ignore[arg-type]

    assert requested == [2]
    assert [h.chunk_id for h in hits] == [h.chunk_id for h in HITS[:2]]
    assert uuid.UUID(str(hits[0].chunk_id))
