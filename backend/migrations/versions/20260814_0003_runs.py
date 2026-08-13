"""Runs: one attempt to perform a skill against a live system

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("skill_id", sa.String(64), nullable=False),
        sa.Column("skill_version", sa.Integer(), nullable=False),
        # The stage is copied, not joined: a promotion tomorrow must not change
        # the record of what this run was permitted to do.
        sa.Column("stage", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_by", sa.String(64), nullable=False),
        sa.Column("authorized_by", sa.String(64)),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        # What the run read out of the system as it went, kept because a step
        # may execute in a different process from the one that read it.
        sa.Column("derived", postgresql.JSONB(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("failure", sa.Text()),
    )
    op.create_index("ix_runs_tenant_started", "runs", ["tenant_id", "started_at"])


def downgrade() -> None:
    op.drop_table("runs")
