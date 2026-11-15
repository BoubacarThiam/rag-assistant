"""Search indexes: HNSW on embeddings (cosine), full-text tsvector column + GIN index.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    # Generated column: PostgreSQL keeps it in sync with `content` automatically
    # (existing rows are computed during this migration).
    op.add_column(
        "chunks",
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('french', content)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index("ix_chunks_content_tsv", "chunks", ["content_tsv"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_chunks_content_tsv", table_name="chunks")
    op.drop_column("chunks", "content_tsv")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
