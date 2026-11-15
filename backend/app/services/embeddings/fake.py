"""Deterministic fake embeddings for tests: no model download, instant, reproducible.

Each word is hashed to one dimension ("hashing trick"), so texts sharing words get close vectors.
That is crude, but enough to test retrieval ranking without the real model.
"""

import hashlib
import math
import re

from app.models.document import EMBEDDING_DIM

WORD_RE = re.compile(r"\w+", re.UNICODE)


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for word in _words(text):
            digest = hashlib.md5(word.encode("utf-8"), usedforsecurity=False).digest()
            vector[int.from_bytes(digest[:4], "little") % self._dimension] += 1.0
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            vector[0] = 1.0  # empty text: arbitrary but valid unit vector
            return vector
        return [x / norm for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def count_tokens(self, text: str) -> int:
        return len(_words(text))
