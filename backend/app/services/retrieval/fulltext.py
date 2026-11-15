"""Keyword search with PostgreSQL full-text search (French stemming).

Complements semantic search: exact terms (product codes, names, numbers like "L.3141-3")
are often better found by words than by meaning.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document
from app.models.document import FULLTEXT_CONFIG
from app.services.retrieval.types import SearchHit

# ts_rank_cd normalization flag 32: rank / (rank + 1), so scores fall in [0, 1).
RANK_NORMALIZATION = 32


async def fulltext_search(
    session: AsyncSession,
    query: str,
    k: int,
    document_ids: Sequence[uuid.UUID] | None = None,
) -> list[SearchHit]:
    # websearch_to_tsquery accepts free text ("congés payés -maladie", "\"mot exact\"")
    # and never fails on user input, unlike to_tsquery.
    tsquery = func.websearch_to_tsquery(FULLTEXT_CONFIG, query)
    rank = func.ts_rank_cd(Chunk.content_tsv, tsquery, RANK_NORMALIZATION).label("rank")

    stmt = (
        select(Chunk, Document.filename, rank)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.content_tsv.op("@@")(tsquery))
        .order_by(rank.desc(), Chunk.id)
        .limit(k)
    )
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))

    rows = await session.execute(stmt)
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=filename,
            content=chunk.content,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            position=chunk.position,
            score=float(score),
        )
        for chunk, filename, score in rows
    ]
