"""Errors are turned into clean JSON, without leaking internals."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import NotFoundError, register_error_handlers


@pytest.fixture
async def error_client() -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Document introuvable.")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    # raise_app_exceptions=False: Starlette re-raises after the 500 handler; we want the response.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_app_error_becomes_json(error_client: AsyncClient) -> None:
    response = await error_client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Document introuvable.", "code": "not_found"}


async def test_unexpected_error_hides_details(error_client: AsyncClient) -> None:
    response = await error_client.get("/boom")
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "secret" not in response.text
