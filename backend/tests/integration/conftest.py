"""Integration fixtures: a real PostgreSQL + pgvector test database.

If the database is unreachable (e.g. Docker not running), every integration test is skipped
instead of failing.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).parents[2]


def _test_db_url() -> str:
    return get_settings().test_database_url


async def _can_connect(url: str) -> bool:
    try:
        conn = await asyncpg.connect(
            url.replace("postgresql+asyncpg://", "postgresql://"), timeout=2
        )
    except (OSError, asyncpg.PostgresError, TimeoutError):
        return False
    await conn.close()
    return True


@pytest.fixture(scope="session")
def migrated_db() -> str:
    url = _test_db_url()
    if not asyncio.run(_can_connect(url)):
        pytest.skip(f"Test database unreachable ({url.split('@')[-1]}): start it with Docker")

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return url


@pytest.fixture
async def db_session(migrated_db: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
        await session.rollback()
    await engine.dispose()
