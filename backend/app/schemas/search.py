import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.services.retrieval.types import SearchMode

Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class SearchRequest(BaseModel):
    query: Query
    k: int | None = Field(default=None, ge=1, le=50, description="Défaut : RETRIEVAL_TOP_K")
    mode: SearchMode | None = Field(default=None, description="Défaut : RETRIEVAL_MODE")
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Limiter la recherche à ces documents"
    )


class SearchResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_start: int
    page_end: int
    position: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    k: int
    results: list[SearchResultOut]
