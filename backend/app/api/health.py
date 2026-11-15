"""Healthcheck: is the API up, and can it reach PostgreSQL with pgvector installed?"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.db import get_session
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

DB_CHECK_TIMEOUT_S = 3.0


@router.get("/health", response_model=HealthResponse)
async def health(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> HealthResponse:
    try:
        async with asyncio.timeout(DB_CHECK_TIMEOUT_S):
            await session.execute(text("SELECT 1"))
            pgvector_version = await session.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
    except Exception:  # any DB failure (refused, timeout, auth...) means "degraded"
        logger.exception("Database healthcheck failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", version=__version__, database="error")

    return HealthResponse(
        status="ok",
        version=__version__,
        database="ok",
        pgvector=str(pgvector_version) if pgvector_version else None,
    )
