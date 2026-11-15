"""Checks against a real migrated database."""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.main import app
from app.models import EMBEDDING_DIM, Chunk, Document

pytestmark = pytest.mark.integration


async def test_health_with_real_database(client: AsyncClient, db_session: AsyncSession) -> None:
    async def _get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _get_session

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["pgvector"]  # e.g. "0.8.0"


async def test_migration_created_all_tables(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    assert {"documents", "chunks", "conversations", "messages"} <= set(rows.scalars())


async def test_chunk_embedding_round_trip(db_session: AsyncSession) -> None:
    document = Document(filename="test.pdf", content_hash="a" * 64, size_bytes=123)
    vector = [0.0] * EMBEDDING_DIM
    vector[0] = 1.0
    document.chunks.append(
        Chunk(
            position=0, page_start=1, page_end=1, content="Bonjour", token_count=3, embedding=vector
        )
    )
    db_session.add(document)
    await db_session.flush()

    stored = await db_session.scalar(select(Chunk).where(Chunk.document_id == document.id))

    assert stored is not None
    assert len(stored.embedding) == EMBEDDING_DIM
    assert stored.embedding[0] == pytest.approx(1.0)
    assert document.status == "processing"
