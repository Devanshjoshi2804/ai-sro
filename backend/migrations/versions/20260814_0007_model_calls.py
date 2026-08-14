"""What left the deployment, and what came back

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_calls",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Names only. A redaction that recorded the values it removed would be
        # a credential store with an apologetic column name.
        sa.Column(
            "redacted_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("outcome", sa.Text(), nullable=False, server_default=""),
        sa.Column("failed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_model_calls_run", "model_calls", ["tenant_id", "run_id", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_model_calls_run", table_name="model_calls")
    op.drop_table("model_calls")
