"""Shared FastAPI dependencies (overridable in tests via `app.dependency_overrides`)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import get_session, get_session_factory
from app.services.embeddings import EmbeddingProvider, get_embedding_provider

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
EmbedderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
