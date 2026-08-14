"""Threads: what was asked, what it was taken to mean

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threads",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("opened_by", sa.String(64), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        # One document: a thread is read whole, never queried by message.
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index("ix_threads_tenant_opened", "threads", ["tenant_id", "opened_at"])


def downgrade() -> None:
    op.drop_index("ix_threads_tenant_opened", table_name="threads")
    op.drop_table("threads")
