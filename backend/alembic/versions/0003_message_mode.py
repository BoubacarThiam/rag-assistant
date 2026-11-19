"""Answer mode of assistant messages: "documents" (strict) or "general" (general knowledge).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: user messages have no mode, and answers stored before this change were all
    # "documents" answers (the API treats a missing mode that way).
    op.add_column("messages", sa.Column("mode", sa.String(20), nullable=True))
    op.create_check_constraint(
        op.f("ck_messages_mode"), "messages", "mode IS NULL OR mode IN ('documents', 'general')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_messages_mode"), "messages", type_="check")
    op.drop_column("messages", "mode")
