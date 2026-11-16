"""Single-container mode (Hugging Face Spaces): API under /api, frontend build, demo password."""

import base64
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import main
from app.core.config import Settings
from app.core.db import get_session
from app.core.demo_auth import password_matches


def basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


class FakeSession:
    async def execute(self, *_: Any) -> None:
        return None

    async def scalar(self, *_: Any) -> str:
        return "0.8.0"


def build_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **overrides: Any) -> FastAPI:
    (tmp_path / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        api_prefix="/api",
        static_dir=str(tmp_path),
        **overrides,
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app()

    async def session() -> AsyncIterator[FakeSession]:
        yield FakeSession()

    app.dependency_overrides[get_session] = session
    return app


def client_for(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_serves_frontend_and_api_under_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async with client_for(build_app(monkeypatch, tmp_path)) as client:
        page = await client.get("/")
        health = await client.get("/api/health")
    assert page.status_code == 200
    assert '<div id="root">' in page.text
    assert health.status_code == 200
    assert health.json()["database"] == "ok"


async def test_demo_password_protects_everything_but_health(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = build_app(monkeypatch, tmp_path, demo_password="secret")
    async with client_for(app) as client:
        anonymous = await client.get("/")
        wrong = await client.get("/", headers={"Authorization": basic("demo", "nope")})
        right = await client.get("/", headers={"Authorization": basic("anyone", "secret")})
        health = await client.get("/api/health")
    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"].startswith("Basic ")
    assert anonymous.json()["code"] == "auth_required"
    assert wrong.status_code == 401
    assert right.status_code == 200
    assert health.status_code == 200


@pytest.mark.parametrize("header", [None, "Bearer x", "Basic not-base64!", basic("u", "")])
def test_malformed_or_missing_credentials_are_rejected(header: str | None) -> None:
    assert not password_matches(header, "secret")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.neon.tech/db?ssl=require",
        ),
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_hosted_database_urls_are_adapted_to_asyncpg(given: str, expected: str) -> None:
    settings = Settings(_env_file=None, database_url=given)  # type: ignore[call-arg]
    assert settings.database_url == expected
