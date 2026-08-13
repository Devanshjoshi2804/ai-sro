"""Connections: a system a tenant has authenticated to

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target_system", sa.String(64), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authenticated_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
    )
    # No credential column anywhere: a connection holds vault keys, never values.
    op.create_index(
        "uq_connections_tenant_system",
        "connections",
        ["tenant_id", "target_system"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("connections")
