"""Semantic search: the chunks whose embedding is closest to the question's embedding."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document
from app.services.retrieval.types import SearchHit


async def vector_search(
    session: AsyncSession,
    query_embedding: list[float],
    k: int,
    document_ids: Sequence[uuid.UUID] | None = None,
) -> list[SearchHit]:
    # HNSW explores `ef_search` candidates (default 40): it must be at least k.
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {max(40, 2 * k)}"))
    if document_ids:
        # With a filter, HNSW finds neighbours first and filters after, which can return fewer
        # than k rows. Iterative scans (pgvector >= 0.8) keep searching until k rows match.
        await session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))

    # `<=>` is cosine distance (0 = same direction, 2 = opposite). similarity = 1 - distance.
    distance = Chunk.embedding.cosine_distance(query_embedding)
    nearest = select(Chunk.id, distance.label("distance")).order_by(distance).limit(k)
    if document_ids:
        nearest = nearest.where(Chunk.document_id.in_(document_ids))
    # Inner query = index-friendly (only the chunks table); the join adds the file name.
    nearest_sq = nearest.subquery()

    rows = await session.execute(
        select(Chunk, Document.filename, nearest_sq.c.distance)
        .join(nearest_sq, nearest_sq.c.id == Chunk.id)
        .join(Document, Document.id == Chunk.document_id)
        .order_by(nearest_sq.c.distance)
    )
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=filename,
            content=chunk.content,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            position=chunk.position,
            score=1.0 - float(dist),
        )
        for chunk, filename, dist in rows
    ]
