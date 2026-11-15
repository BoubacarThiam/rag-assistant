import uuid
from dataclasses import dataclass
from typing import Literal

SearchMode = Literal["vector", "fulltext", "hybrid"]


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    page_start: int
    page_end: int
    position: int
    # Higher is better. Its meaning depends on the method:
    # vector = cosine similarity (-1..1), fulltext = normalized rank (0..1), hybrid = RRF score.
    score: float
