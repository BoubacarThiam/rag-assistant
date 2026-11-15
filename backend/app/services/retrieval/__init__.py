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
from app.services.retrieval.reranker import Reranker, rerank
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
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    start = time.perf_counter()
    # With a reranker, fetch more candidates than needed: it will keep the best k.
    fetch = max(k, settings.rerank_candidates) if reranker else k

    if mode == "fulltext":
        hits = await fulltext_search(session, query, fetch, document_ids)
    else:
        query_embedding = await asyncio.to_thread(embedder.embed_query, query)
        if mode == "vector":
            hits = await vector_search(session, query_embedding, fetch, document_ids)
        else:
            candidates = max(fetch, settings.hybrid_candidates)
            vector_hits = await vector_search(session, query_embedding, candidates, document_ids)
            text_hits = await fulltext_search(session, query, candidates, document_ids)
            hits = rrf_fuse([vector_hits, text_hits], k=fetch, rrf_k=settings.rrf_k)

    if reranker:
        hits = await asyncio.to_thread(rerank, reranker, query, hits, k)

    logger.info(
        "Search mode=%s rerank=%s k=%d filter=%d docs -> %d hits in %.0f ms",
        mode,
        bool(reranker),
        k,
        len(document_ids or []),
        len(hits),
        (time.perf_counter() - start) * 1000,
    )
    return hits


__all__ = ["Reranker", "SearchHit", "SearchMode", "rerank", "rrf_fuse", "search"]
