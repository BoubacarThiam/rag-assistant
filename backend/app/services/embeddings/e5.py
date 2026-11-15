"""Local multilingual embeddings with intfloat/multilingual-e5-base (sentence-transformers)."""

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# E5 models were trained with these prefixes: forgetting them noticeably degrades retrieval.
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


class E5EmbeddingProvider:
    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None
        # The model is loaded once and shared; this lock serializes loading and encoding.
        self._lock = threading.Lock()

    def _get_model(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy import, done lazily

            logger.info("Loading embedding model %s (first run downloads it)...", self.model_name)
            start = time.perf_counter()
            self._model = SentenceTransformer(self.model_name, device="cpu")
            logger.info("Embedding model loaded in %.1fs", time.perf_counter() - start)
        return self._model

    @property
    def dimension(self) -> int:
        with self._lock:
            dim = self._get_model().get_sentence_embedding_dimension()
        assert dim is not None
        return int(dim)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            vectors: Any = self._get_model().encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,  # unit vectors -> cosine similarity = dot product
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        return [[float(x) for x in vector] for vector in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([PASSAGE_PREFIX + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0]

    def count_tokens(self, text: str) -> int:
        with self._lock:
            tokenizer: Any = self._get_model().tokenizer
            ids = tokenizer.encode(text, add_special_tokens=False, verbose=False)
        return len(ids)
