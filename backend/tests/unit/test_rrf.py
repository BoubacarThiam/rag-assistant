import uuid

import pytest

from app.services.retrieval import SearchHit, rrf_fuse


def hit(name: str, score: float = 0.0) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid5(uuid.NAMESPACE_DNS, name),
        document_id=uuid.uuid4(),
        document_name="doc.pdf",
        content=name,
        page_start=1,
        page_end=1,
        position=0,
        score=score,
    )


def names(hits: list[SearchHit]) -> list[str]:
    return [h.content for h in hits]


def test_item_found_by_both_methods_wins() -> None:
    vector = [hit("A"), hit("B"), hit("C")]
    fulltext = [hit("D"), hit("C"), hit("E")]

    fused = rrf_fuse([vector, fulltext], k=5)

    # C: 1/63 + 1/62 beats A: 1/61 alone.
    assert names(fused)[0] == "C"
    assert set(names(fused)) == {"A", "B", "C", "D", "E"}


def test_scores_follow_the_formula_and_are_sorted() -> None:
    fused = rrf_fuse([[hit("A"), hit("B")], [hit("B")]], k=2, rrf_k=60)

    assert names(fused) == ["B", "A"]
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].score == pytest.approx(1 / 61)


def test_original_scales_are_ignored() -> None:
    # A huge raw score on one list must not dominate: only ranks count.
    fused = rrf_fuse([[hit("A", 1000.0), hit("B", 999.0)], [hit("B", 0.01)]], k=2)
    assert names(fused)[0] == "B"


def test_k_limits_the_results_and_duplicates_are_merged() -> None:
    ranking = [hit(str(i)) for i in range(10)]
    fused = rrf_fuse([ranking, ranking], k=3)
    assert names(fused) == ["0", "1", "2"]


def test_empty_rankings() -> None:
    assert rrf_fuse([[], []], k=5) == []
