"""Ingestion pipeline: PDF bytes -> pages -> clean text -> chunks -> embeddings -> database.

`process_pdf` is pure CPU work (no database), easy to test. `ingest_document` runs it in a thread
and stores the result; it is launched as a background task after the upload response.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import Chunk, Document, DocumentStatus
from app.services.embeddings.base import EmbeddingProvider
from app.services.ingestion.chunking import ChunkDraft, chunk_pages
from app.services.ingestion.cleaning import clean_pages
from app.services.ingestion.extraction import PdfExtractionError, extract_pages

logger = logging.getLogger(__name__)

NO_TEXT_MESSAGE = (
    "Aucun texte n'a pu être extrait de ce PDF (document scanné ?). "
    "La reconnaissance de texte (OCR) n'est pas prise en charge."
)
UNEXPECTED_MESSAGE = "Erreur inattendue pendant le traitement du document."
INTERRUPTED_MESSAGE = "Traitement interrompu par un redémarrage du serveur. Réimportez le document."


@dataclass(frozen=True)
class ProcessedDocument:
    page_count: int
    chunks: list[ChunkDraft]
    embeddings: list[list[float]]


def process_pdf(
    data: bytes, embedder: EmbeddingProvider, chunk_size: int, overlap: int, batch_size: int
) -> ProcessedDocument:
    pages = clean_pages(extract_pages(data))
    if not any(page.text for page in pages):
        raise PdfExtractionError(NO_TEXT_MESSAGE)

    chunks = chunk_pages(pages, embedder.count_tokens, chunk_size, overlap)
    embeddings: list[list[float]] = []
    # Batch by batch: between batches, other requests (searches) can use the model.
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embeddings.extend(embedder.embed_documents([chunk.text for chunk in batch]))
    return ProcessedDocument(page_count=len(pages), chunks=chunks, embeddings=embeddings)


async def _mark_error(
    session_factory: async_sessionmaker[AsyncSession], document_id: uuid.UUID, message: str
) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=DocumentStatus.ERROR.value, error_message=message)
        )
        await session.commit()


async def ingest_document(
    document_id: uuid.UUID,
    data: bytes,
    session_factory: async_sessionmaker[AsyncSession],
    embedder: EmbeddingProvider,
    settings: Settings,
) -> None:
    start = time.perf_counter()
    logger.info("Ingestion started: document=%s size=%d bytes", document_id, len(data))
    try:
        result = await asyncio.to_thread(
            process_pdf,
            data,
            embedder,
            settings.chunk_size_tokens,
            settings.chunk_overlap_tokens,
            settings.embedding_batch_size,
        )
        async with session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                logger.warning("Document %s deleted during ingestion, result dropped", document_id)
                return
            session.add_all(
                Chunk(
                    document_id=document_id,
                    position=draft.position,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    content=draft.text,
                    token_count=draft.token_count,
                    embedding=embedding,
                )
                for draft, embedding in zip(result.chunks, result.embeddings, strict=True)
            )
            document.page_count = result.page_count
            document.chunk_count = len(result.chunks)
            document.status = DocumentStatus.READY.value
            document.error_message = None
            await session.commit()
    except PdfExtractionError as exc:
        logger.info("Ingestion rejected: document=%s reason=%s", document_id, exc)
        await _mark_error(session_factory, document_id, str(exc))
        return
    except Exception:
        logger.exception("Ingestion failed: document=%s", document_id)
        await _mark_error(session_factory, document_id, UNEXPECTED_MESSAGE)
        return

    logger.info(
        "Ingestion done: document=%s pages=%d chunks=%d in %.1fs",
        document_id,
        result.page_count,
        len(result.chunks),
        time.perf_counter() - start,
    )


async def recover_interrupted_documents(session_factory: async_sessionmaker[AsyncSession]) -> int:
    """At startup, documents still "processing" belong to a task that died with the old process.

    Valid because the API runs as a single process; with several workers, a job queue would be
    needed instead of background tasks.
    """
    async with session_factory() as session:
        result = await session.execute(
            update(Document)
            .where(Document.status == DocumentStatus.PROCESSING.value)
            .values(status=DocumentStatus.ERROR.value, error_message=INTERRUPTED_MESSAGE)
        )
        await session.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    return count
