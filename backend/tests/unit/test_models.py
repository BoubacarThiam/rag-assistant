"""The SQLAlchemy models and the initial migration must describe the same schema."""

import importlib.util
from pathlib import Path
from types import ModuleType

from app.models import EMBEDDING_DIM, Base

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0001_initial_schema.py"


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0001", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {"documents", "chunks", "conversations", "messages"}


def test_embedding_dimension_matches_migration() -> None:
    assert load_migration().EMBEDDING_DIM == EMBEDDING_DIM
    assert Base.metadata.tables["chunks"].c.embedding.type.dim == EMBEDDING_DIM


def test_deleting_a_document_cascades_to_chunks() -> None:
    (fk,) = Base.metadata.tables["chunks"].c.document_id.foreign_keys
    assert fk.ondelete == "CASCADE"
