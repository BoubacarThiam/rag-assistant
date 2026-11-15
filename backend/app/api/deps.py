"""Shared FastAPI dependencies (overridable in tests via `app.dependency_overrides`)."""

import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import get_session, get_session_factory
from app.services.chat import Retriever
from app.services.conversations import ConversationStore, SqlConversationStore
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.llm import LLMProvider, get_llm_provider
from app.services.retrieval import SearchHit, search

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
EmbedderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]


def get_conversation_store(session_factory: SessionFactoryDep) -> ConversationStore:
    return SqlConversationStore(session_factory)


def get_retriever(
    session_factory: SessionFactoryDep, embedder: EmbedderDep, settings: SettingsDep
) -> Retriever:
    async def retrieve(query: str, document_ids: Sequence[uuid.UUID] | None) -> list[SearchHit]:
        # Own short session: released before the (long) LLM stream starts.
        async with session_factory() as session:
            return await search(
                session,
                embedder,
                settings,
                query,
                k=settings.retrieval_top_k,
                mode=settings.retrieval_mode,
                document_ids=document_ids,
            )

    return retrieve


ConversationStoreDep = Annotated[ConversationStore, Depends(get_conversation_store)]
RetrieverDep = Annotated[Retriever, Depends(get_retriever)]
