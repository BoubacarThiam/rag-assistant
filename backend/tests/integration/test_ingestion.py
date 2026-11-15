"""Full upload -> background ingestion -> stored chunks, against a real database."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Chunk
from tests.pdf_factory import make_pdf

pytestmark = pytest.mark.integration

BODY = " ".join(f"Article {i} : les salariés ont droit à des congés payés." for i in range(1, 30))


async def wait_until_done(client: AsyncClient, document_id: str) -> dict:  # type: ignore[type-arg]
    for _ in range(50):
        body = (await client.get(f"/documents/{document_id}")).json()
        if body["status"] != "processing":
            return body  # type: ignore[no-any-return]
        await asyncio.sleep(0.1)
    raise AssertionError("ingestion did not finish")


async def upload(client: AsyncClient, name: str, data: bytes) -> list[dict]:  # type: ignore[type-arg]
    response = await client.post("/documents", files=[("files", (name, data, "application/pdf"))])
    assert response.status_code == 202, response.text
    return response.json()  # type: ignore[no-any-return]


async def test_upload_then_document_becomes_ready(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    (created,) = await upload(client, "reglement.pdf", make_pdf([BODY, BODY]))
    assert created["status"] == "processing"

    document = await wait_until_done(client, created["id"])

    assert document["status"] == "ready"
    assert document["page_count"] == 2
    assert document["chunk_count"] > 0
    async with factory() as session:
        chunks = list(
            await session.scalars(
                select(Chunk)
                .where(Chunk.document_id == uuid.UUID(created["id"]))
                .order_by(Chunk.position)
            )
        )
    assert len(chunks) == document["chunk_count"]
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2


async def test_several_files_in_one_upload(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    files = [("files", (f"doc{i}.pdf", make_pdf([f"Document {i}. {BODY}"]), "application/pdf"))
             for i in range(2)]  # fmt: skip
    response = await client.post("/documents", files=files)
    assert response.status_code == 202
    assert len((await client.get("/documents")).json()) == 2


async def test_duplicate_upload_is_rejected(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    pdf = make_pdf([BODY])
    await upload(client, "a.pdf", pdf)

    response = await client.post("/documents", files=[("files", ("b.pdf", pdf, "application/pdf"))])

    assert response.status_code == 409
    assert "a.pdf" in response.json()["detail"]


async def test_scanned_pdf_ends_in_error_status(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    (created,) = await upload(client, "scan.pdf", make_pdf([""]))

    document = await wait_until_done(client, created["id"])

    assert document["status"] == "error"
    assert "Aucun texte" in document["error_message"]


async def test_delete_removes_document_and_chunks(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    (created,) = await upload(client, "a.pdf", make_pdf([BODY]))
    await wait_until_done(client, created["id"])

    assert (await client.delete(f"/documents/{created['id']}")).status_code == 204
    assert (await client.get(f"/documents/{created['id']}")).status_code == 404
    async with factory() as session:
        assert await session.scalar(select(Chunk.id).limit(1)) is None


async def test_unknown_document_is_404(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession]
) -> None:
    response = await client.get(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document introuvable."
