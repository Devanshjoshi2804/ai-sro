"""Initial schema: recordings and skills

Revision ID: 0001
Revises:
Create Date: 2026-08-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recordings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("objective_type", sa.String(64), nullable=False),
        sa.Column("target_system", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("facility", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("demonstrator", sa.String(64), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("browser_session_id", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("abandon_reason", sa.Text()),
        sa.Column("frames", postgresql.JSONB(), nullable=False),
        sa.Column("artifacts", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_recordings_tenant_started", "recordings", ["tenant_id", "started_at"])
    op.create_index(
        "ix_recordings_tenant_objective",
        "recordings",
        [
            "tenant_id",
            "objective_type",
            "target_system",
            "entity_type",
            "facility",
            "direction",
        ],
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("objective_type", sa.String(64), nullable=False),
        sa.Column("target_system", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("facility", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_version", sa.Integer(), nullable=False),
        sa.Column("latest_stage", sa.String(16), nullable=False),
        sa.Column("versions", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "uq_skills_tenant_objective",
        "skills",
        [
            "tenant_id",
            "objective_type",
            "target_system",
            "entity_type",
            "facility",
            "direction",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("skills")
    op.drop_table("recordings")
