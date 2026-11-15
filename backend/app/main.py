"""FastAPI application entry point."""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import documents, health, search
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.services.ingestion.pipeline import recover_interrupted_documents

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting %s v%s (env=%s)", settings.app_name, __version__, settings.environment)
    try:
        recovered = await recover_interrupted_documents(SessionLocal)
        if recovered:
            logger.warning("%d interrupted document(s) marked as error", recovered)
    except Exception:  # the API must start even if the database is not ready yet
        logger.exception("Could not check for interrupted documents")
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    return app


app = create_app()
