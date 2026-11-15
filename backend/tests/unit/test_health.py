"""/health without a real database: the session is replaced by a fake."""

from collections.abc import AsyncIterator
from typing import Any

from httpx import AsyncClient

from app import __version__
from app.core.db import get_session
from app.main import app


class FakeSession:
    def __init__(self, pgvector_version: str | None = "0.8.0", fail: bool = False) -> None:
        self.pgvector_version = pgvector_version
        self.fail = fail

    async def execute(self, *_: Any) -> None:
        if self.fail:
            raise OSError("connection refused")

    async def scalar(self, *_: Any) -> str | None:
        return self.pgvector_version


def override_session(session: FakeSession) -> None:
    async def _get_session() -> AsyncIterator[FakeSession]:
        yield session

    app.dependency_overrides[get_session] = _get_session


async def test_health_ok(client: AsyncClient) -> None:
    override_session(FakeSession())

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "database": "ok",
        "pgvector": "0.8.0",
    }


async def test_health_reports_missing_pgvector(client: AsyncClient) -> None:
    override_session(FakeSession(pgvector_version=None))

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["pgvector"] is None


async def test_health_degraded_when_database_unreachable(client: AsyncClient) -> None:
    override_session(FakeSession(fail=True))

    response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"
