"""Reciprocal Rank Fusion (RRF): merge several ranked lists into one.

Vector scores (cosine) and full-text scores (ts_rank) are not on the same scale, so adding them
makes no sense. RRF only uses each result's *rank*:

    score(chunk) = sum over lists of 1 / (rrf_k + rank in that list)     (rank starts at 1)

A chunk found by both methods accumulates two contributions and rises to the top.
rrf_k (60 in the original paper) dampens the gap between rank 1 and rank 2.
"""

import uuid
from dataclasses import replace

from app.services.retrieval.types import SearchHit


def rrf_fuse(rankings: list[list[SearchHit]], k: int, rrf_k: int = 60) -> list[SearchHit]:
    scores: dict[uuid.UUID, float] = {}
    hits: dict[uuid.UUID, SearchHit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            hits.setdefault(hit.chunk_id, hit)

    # Ties broken by first appearance (dicts keep insertion order, sort is stable).
    ordered = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    return [replace(hits[chunk_id], score=scores[chunk_id]) for chunk_id in ordered[:k]]
