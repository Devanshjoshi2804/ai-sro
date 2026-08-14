"""What is known about a system, with the evidence behind each claim

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DIMENSIONS = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("system", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("evidence", sa.String(16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        # Nothing is deleted or rewritten: a superseded claim points forward at
        # what replaced it, so "we used to believe this" survives.
        sa.Column("superseded_by", sa.String(64), nullable=True),
        sa.Column("embedding", Vector(_DIMENSIONS), nullable=True),
    )
    # Partial: retrieval only ever asks about what is currently believed, and
    # the history is what makes the full table large.
    op.create_index(
        "ix_knowledge_current",
        "knowledge_entries",
        ["tenant_id", "system", "kind", "key"],
        postgresql_where=sa.text("superseded_by IS NULL"),
    )
    op.create_index("ix_knowledge_tenant_kind", "knowledge_entries", ["tenant_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_tenant_kind", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_current", table_name="knowledge_entries")
    op.drop_table("knowledge_entries")
