"""Which system a run touched, so safety can ask about a system

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-14

The track record and demotion reason live inside the skill's versions JSONB and
need no migration: the codec derives its shape from the domain's own types.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("target_system", sa.String(64), nullable=False, server_default=""),
    )
    # The circuit breaker's only question: how has this system behaved lately.
    op.create_index("ix_runs_system_ended", "runs", ["tenant_id", "target_system", "ended_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_system_ended", table_name="runs")
    op.drop_column("runs", "target_system")
