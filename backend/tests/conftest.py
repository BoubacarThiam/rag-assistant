"""Shared fixtures for the whole test suite."""

import os
from collections.abc import AsyncIterator

# Before importing the app: a developer's .env may hold deployment settings (demo password,
# single-container mode) that must not apply to the tests. Environment variables take
# precedence over .env.
os.environ.update(DEMO_PASSWORD="", API_PREFIX="", STATIC_DIR="")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
