"""Reranking: a second, more precise model re-orders the passages found by the search.

The embedding model (a "bi-encoder") turns the question and each passage into vectors
*separately*: fast, but it never reads them together. A "cross-encoder" reads the question and
one passage *together* and outputs a relevance score: much more precise, but too slow to run on
the whole corpus. So we combine them: the search fetches ~20 candidates quickly, the
cross-encoder re-orders only those, and we keep the best k.
"""

import logging
import math
import re
import threading
import time
from dataclasses import replace
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Protocol

from app.core.config import get_settings
from app.services.ingestion.context import contextualize
from app.services.retrieval.types import SearchHit

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]:
        """One relevance score in [0, 1] per passage (higher is better)."""
        ...


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: CrossEncoder | None = None
        self._lock = threading.Lock()

    def _get_model(self) -> "CrossEncoder":
        if self._model is None:
            from sentence_transformers import CrossEncoder  # heavy import, done lazily

            logger.info("Loading reranker %s (first run downloads it)...", self.model_name)
            start = time.perf_counter()
            self._model = CrossEncoder(self.model_name, device="cpu")
            logger.info("Reranker loaded in %.1fs", time.perf_counter() - start)
        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        with self._lock:
            logits: Any = self._get_model().predict(
                [(query, passage) for passage in passages], show_progress_bar=False
            )
        # Raw scores are unbounded logits: squash them to (0, 1) for display.
        return [1.0 / (1.0 + math.exp(-float(logit))) for logit in logits]


class FakeReranker:
    """For tests: share of the query's words found in the passage."""

    def score(self, query: str, passages: list[str]) -> list[float]:
        words = set(re.findall(r"\w+", query.lower()))
        return [
            len(words & set(re.findall(r"\w+", passage.lower()))) / max(len(words), 1)
            for passage in passages
        ]


def rerank(reranker: Reranker, query: str, hits: list[SearchHit], k: int) -> list[SearchHit]:
    """Re-order `hits` by the reranker's score and keep the best k (ties keep search order)."""
    # The reranker reads each passage with its document title, for the same reason as embeddings.
    passages = [contextualize(hit.document_name, hit.content) for hit in hits]
    scores = reranker.score(query, passages)
    order = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)
    return [replace(hits[i], score=scores[i]) for i in order[:k]]


@lru_cache
def get_reranker() -> Reranker | None:
    """FastAPI dependency: the shared reranker, or None when reranking is disabled."""
    settings = get_settings()
    return CrossEncoderReranker(settings.reranker_model) if settings.rerank_enabled else None
