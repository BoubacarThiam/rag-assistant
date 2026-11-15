from fastapi import APIRouter

from app.api.deps import EmbedderDep, RerankerDep, SessionDep, SettingsDep
from app.schemas.search import SearchRequest, SearchResponse, SearchResultOut
from app.services.retrieval import search

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_chunks(
    request: SearchRequest,
    session: SessionDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    reranker: RerankerDep,
) -> SearchResponse:
    """Top-k passages for a question, with their similarity score."""
    k = request.k or settings.retrieval_top_k
    mode = request.mode or settings.retrieval_mode
    hits = await search(
        session,
        embedder,
        settings,
        request.query,
        k=k,
        mode=mode,
        document_ids=request.document_ids,
        reranker=reranker,
    )
    return SearchResponse(
        query=request.query,
        mode=mode,
        k=k,
        results=[SearchResultOut.model_validate(hit) for hit in hits],
    )
