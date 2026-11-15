"""/search request handling, with the search service replaced by a stub."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from app.api import search as search_api
from app.services.retrieval import SearchHit

HIT = SearchHit(
    chunk_id=uuid.uuid4(),
    document_id=uuid.uuid4(),
    document_name="guide.pdf",
    content="Les congés payés sont de 25 jours.",
    page_start=3,
    page_end=4,
    position=7,
    score=0.83,
)


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []

    async def fake_search(*args: Any, **kwargs: Any) -> list[SearchHit]:
        recorded.append({"query": args[3], **kwargs})
        return [HIT]

    monkeypatch.setattr(search_api, "search", fake_search)
    return recorded


async def test_returns_results_with_defaults(
    client: AsyncClient, calls: list[dict[str, Any]]
) -> None:
    response = await client.post("/search", json={"query": "  congés  "})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "congés"  # whitespace stripped
    assert body["mode"] == "vector"
    assert body["k"] == 5
    assert body["results"][0] == {
        "chunk_id": str(HIT.chunk_id),
        "document_id": str(HIT.document_id),
        "document_name": "guide.pdf",
        "page_start": 3,
        "page_end": 4,
        "position": 7,
        "content": HIT.content,
        "score": 0.83,
    }
    assert calls[0] == {"query": "congés", "k": 5, "mode": "vector", "document_ids": None}


async def test_passes_options_through(client: AsyncClient, calls: list[dict[str, Any]]) -> None:
    doc_id = uuid.uuid4()
    response = await client.post(
        "/search",
        json={"query": "q", "k": 10, "mode": "hybrid", "document_ids": [str(doc_id)]},
    )
    assert response.status_code == 200
    assert calls[0]["k"] == 10
    assert calls[0]["mode"] == "hybrid"
    assert calls[0]["document_ids"] == [doc_id]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "q", "k": 0},
        {"query": "q", "k": 51},
        {"query": "q", "mode": "magic"},
        {"query": "q", "document_ids": ["not-a-uuid"]},
        {"query": "x" * 1001},
    ],
)
async def test_invalid_requests_are_rejected(
    client: AsyncClient, calls: list[dict[str, Any]], payload: dict[str, Any]
) -> None:
    assert (await client.post("/search", json=payload)).status_code == 422
    assert calls == []
