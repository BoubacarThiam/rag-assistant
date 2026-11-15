"""Retrieval entry point: one `search` function for the three modes."""

import asyncio
import logging
import time
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.retrieval.fulltext import fulltext_search
from app.services.retrieval.hybrid import rrf_fuse
from app.services.retrieval.types import SearchHit, SearchMode
from app.services.retrieval.vector import vector_search

logger = logging.getLogger(__name__)


async def search(
    session: AsyncSession,
    embedder: EmbeddingProvider,
    settings: Settings,
    query: str,
    *,
    k: int,
    mode: SearchMode,
    document_ids: Sequence[uuid.UUID] | None = None,
) -> list[SearchHit]:
    start = time.perf_counter()

    if mode == "fulltext":
        hits = await fulltext_search(session, query, k, document_ids)
    else:
        query_embedding = await asyncio.to_thread(embedder.embed_query, query)
        if mode == "vector":
            hits = await vector_search(session, query_embedding, k, document_ids)
        else:
            candidates = max(k, settings.hybrid_candidates)
            vector_hits = await vector_search(session, query_embedding, candidates, document_ids)
            text_hits = await fulltext_search(session, query, candidates, document_ids)
            hits = rrf_fuse([vector_hits, text_hits], k=k, rrf_k=settings.rrf_k)

    logger.info(
        "Search mode=%s k=%d filter=%d docs -> %d hits in %.0f ms",
        mode,
        k,
        len(document_ids or []),
        len(hits),
        (time.perf_counter() - start) * 1000,
    )
    return hits


__all__ = ["SearchHit", "SearchMode", "rrf_fuse", "search"]
