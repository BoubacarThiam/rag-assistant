"""Where the evaluation corpus is indexed and searched.

- PgBackend: the real thing. A dedicated database (never the user's data), filled through the
  application's own ingestion, searched with the application's own `search` (pgvector HNSW,
  full-text, hybrid).
- MemoryBackend: no database needed. Same extraction, cleaning, chunking and embeddings, but
  vectors are kept in memory and compared exactly (cosine). Vector mode only. Useful to measure
  the embedding model and the chunking when PostgreSQL is not available.
"""

import asyncio
import hashlib
import logging
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Protocol

import asyncpg
import numpy as np
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models import Document, DocumentStatus
from app.services.embeddings.base import EmbeddingProvider
from app.services.ingestion.pipeline import ingest_document, process_pdf
from app.services.retrieval import Reranker, SearchHit, SearchMode, rerank, search

logger = logging.getLogger(__name__)


class Backend(Protocol):
    name: str

    async def setup(self, pdf_paths: list[Path]) -> int:
        """Index the PDFs from scratch; returns the number of chunks."""
        ...

    async def search(self, query: str, k: int, mode: SearchMode) -> list[SearchHit]: ...

    async def close(self) -> None: ...


class MemoryBackend:
    name = "memory (cosinus exact, sans pgvector)"

    def __init__(
        self, embedder: EmbeddingProvider, settings: Settings, reranker: Reranker | None = None
    ) -> None:
        self._embedder = embedder
        self._settings = settings
        self._reranker = reranker
        self._hits: list[SearchHit] = []
        self._matrix = np.zeros((0, 0), dtype=np.float32)

    async def setup(self, pdf_paths: list[Path]) -> int:
        vectors: list[list[float]] = []
        self._hits = []
        for path in pdf_paths:
            result = await asyncio.to_thread(
                process_pdf,
                path.read_bytes(),
                self._embedder,
                self._settings.chunk_size_tokens,
                self._settings.chunk_overlap_tokens,
                self._settings.embedding_batch_size,
            )
            document_id = uuid.uuid4()
            for chunk, embedding in zip(result.chunks, result.embeddings, strict=True):
                self._hits.append(
                    SearchHit(
                        chunk_id=uuid.uuid4(),
                        document_id=document_id,
                        document_name=path.name,
                        content=chunk.text,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        position=chunk.position,
                        score=0.0,
                    )
                )
                vectors.append(embedding)
        self._matrix = np.asarray(vectors, dtype=np.float32)
        return len(self._hits)

    async def search(self, query: str, k: int, mode: SearchMode) -> list[SearchHit]:
        if mode != "vector":
            raise ValueError("the memory backend only supports vector search (use PostgreSQL)")
        query_vector = np.asarray(
            await asyncio.to_thread(self._embedder.embed_query, query), dtype=np.float32
        )
        # Vectors are normalized, so the dot product is the cosine similarity.
        scores = self._matrix @ query_vector
        # Same two steps as the application's `search`: candidates, then optional reranking.
        fetch = max(k, self._settings.rerank_candidates) if self._reranker else k
        best = np.argsort(-scores, kind="stable")[:fetch]
        hits = [replace(self._hits[i], score=float(scores[i])) for i in best]
        if self._reranker:
            hits = await asyncio.to_thread(rerank, self._reranker, query, hits, k)
        return hits

    async def close(self) -> None:
        return None


def _asyncpg_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def database_reachable(url: str) -> bool:
    """True if the PostgreSQL server answers (the evaluation database itself may not exist yet)."""
    server_url = _asyncpg_url(url).rsplit("/", 1)[0] + "/postgres"
    try:
        connection = await asyncpg.connect(server_url, timeout=2)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        return False
    await connection.close()
    return True


class PgBackend:
    name = "postgresql + pgvector"

    def __init__(
        self, embedder: EmbeddingProvider, settings: Settings, reranker: Reranker | None = None
    ) -> None:
        self._embedder = embedder
        self._settings = settings
        self._reranker = reranker
        self._url = settings.eval_database_url
        self._engine = create_async_engine(self._url)
        self._sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def _create_database_if_missing(self) -> None:
        base, name = _asyncpg_url(self._url).rsplit("/", 1)
        connection = await asyncpg.connect(f"{base}/postgres")
        try:
            exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
            if not exists:
                await connection.execute(f'CREATE DATABASE "{name}"')
                logger.info("Created evaluation database %s", name)
        finally:
            await connection.close()

    def _migrate(self) -> None:
        config = Config(str(Path(__file__).resolve().parent.parent / "backend" / "alembic.ini"))
        if not Path(config.config_file_name or "").exists():  # inside the API container
            config = Config("alembic.ini")
        config.attributes["configure_logger"] = False
        config.set_main_option("sqlalchemy.url", self._url.replace("%", "%%"))
        command.upgrade(config, "head")

    async def setup(self, pdf_paths: list[Path]) -> int:
        await self._create_database_if_missing()
        await asyncio.to_thread(self._migrate)  # Alembic runs its own event loop
        async with self._engine.begin() as connection:
            await connection.execute(text("TRUNCATE documents, conversations CASCADE"))

        for path in pdf_paths:
            data = path.read_bytes()
            async with self._sessions() as session:
                document = Document(
                    filename=path.name,
                    content_hash=hashlib.sha256(data).hexdigest(),
                    size_bytes=len(data),
                )
                session.add(document)
                await session.commit()
            # The application's own ingestion, exactly as after an upload.
            await ingest_document(document.id, data, self._sessions, self._embedder, self._settings)

        async with self._sessions() as session:
            failed = list(
                await session.scalars(
                    select(Document.filename).where(Document.status != DocumentStatus.READY.value)
                )
            )
            if failed:
                raise RuntimeError(f"ingestion failed for: {', '.join(failed)}")
            count = await session.scalar(text("SELECT count(*) FROM chunks"))
        return int(count or 0)

    async def search(self, query: str, k: int, mode: SearchMode) -> list[SearchHit]:
        async with self._sessions() as session:
            return await search(
                session, self._embedder, self._settings, query,
                k=k, mode=mode, reranker=self._reranker,
            )  # fmt: skip

    async def close(self) -> None:
        await self._engine.dispose()
