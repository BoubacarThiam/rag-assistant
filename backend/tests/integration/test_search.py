"""Search against a real database (pgvector + full-text), with fake embeddings."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models import Chunk, Document, DocumentStatus
from app.services.embeddings import FakeEmbeddingProvider
from app.services.retrieval import search

pytestmark = pytest.mark.integration

EMBEDDER = FakeEmbeddingProvider()

CORPUS = {
    "rh.pdf": [
        "Chaque salarié a droit à 25 jours de congés payés par an.",
        "Les congés doivent être demandés un mois à l'avance.",
        "La mutuelle est prise en charge à 60 % par l'employeur.",
    ],
    "it.pdf": [
        "Le télétravail est possible trois jours par semaine.",
        "Le mot de passe doit contenir au moins douze caractères.",
        "La référence du routeur est XR-4410.",
    ],
}


@pytest.fixture
async def corpus(factory: async_sessionmaker[AsyncSession]) -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    async with factory() as session:
        for filename, passages in CORPUS.items():
            document = Document(
                filename=filename,
                content_hash=uuid.uuid4().hex * 2,
                size_bytes=1,
                page_count=len(passages),
                chunk_count=len(passages),
                status=DocumentStatus.READY.value,
            )
            for position, content in enumerate(passages):
                document.chunks.append(
                    Chunk(
                        position=position,
                        page_start=position + 1,
                        page_end=position + 1,
                        content=content,
                        token_count=len(content.split()),
                        embedding=EMBEDDER.embed_documents([content])[0],
                    )
                )
            session.add(document)
            await session.flush()
            ids[filename] = document.id
        await session.commit()
    return ids


async def run(
    factory: async_sessionmaker[AsyncSession], query: str, mode: str, k: int = 3, **kwargs: object
) -> list:  # type: ignore[type-arg]
    async with factory() as session:
        return await search(session, EMBEDDER, get_settings(), query, k=k, mode=mode, **kwargs)  # type: ignore[arg-type]


async def test_vector_search_ranks_the_relevant_passage_first(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    hits = await run(factory, "jours de congés payés", "vector")

    assert hits[0].content.startswith("Chaque salarié a droit à 25 jours")
    assert hits[0].document_name == "rh.pdf"
    assert hits[0].page_start == 1
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)
    assert -1.0 <= hits[-1].score <= hits[0].score <= 1.0


async def test_k_limits_the_number_of_results(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    assert len(await run(factory, "congés", "vector", k=2)) == 2
    assert len(await run(factory, "congés", "vector", k=50)) == 6


async def test_filter_by_document(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    hits = await run(factory, "congés payés", "vector", k=10, document_ids=[corpus["it.pdf"]])

    assert len(hits) == 3
    assert {h.document_name for h in hits} == {"it.pdf"}


async def test_fulltext_uses_french_stemming(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    # "congé" (singular) matches "congés"; stop words like "le" are ignored.
    hits = await run(factory, "le congé", "fulltext")

    assert {h.content for h in hits} == {CORPUS["rh.pdf"][0], CORPUS["rh.pdf"][1]}
    assert all(0 < h.score < 1 for h in hits)


async def test_fulltext_finds_exact_codes(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    hits = await run(factory, "XR-4410", "fulltext")
    assert [h.content for h in hits] == [CORPUS["it.pdf"][2]]


async def test_fulltext_without_match_returns_nothing(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    assert await run(factory, "photosynthèse", "fulltext") == []


async def test_hybrid_combines_both_methods(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    hits = await run(factory, "congés payés", "hybrid", k=3)

    assert hits[0].content == CORPUS["rh.pdf"][0]  # first in both lists
    assert len({h.chunk_id for h in hits}) == len(hits)  # no duplicates


async def test_hnsw_index_is_usable(
    factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    # On a tiny table PostgreSQL prefers a sequential scan; we forbid it to check the index.
    vector = str(EMBEDDER.embed_query("congés"))
    async with factory() as session:
        await session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = "\n".join(
            row[0]
            for row in await session.execute(
                text(
                    "EXPLAIN SELECT id FROM chunks "
                    "ORDER BY embedding <=> CAST(:v AS vector) LIMIT 3"
                ),
                {"v": vector},
            )
        )
    assert "ix_chunks_embedding_hnsw" in plan


async def test_search_endpoint(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession], corpus: dict[str, uuid.UUID]
) -> None:
    response = await client.post("/search", json={"query": "mot de passe", "k": 1})

    assert response.status_code == 200
    (result,) = response.json()["results"]
    assert result["content"] == CORPUS["it.pdf"][1]
    assert result["document_name"] == "it.pdf"
