"""a folded doing stays placed

A doing the mining pass recognises as a stored job is not saved as a job of
its own, and a doing a job grew into replaces the steps that cited the one
before it. Either way nothing in `workflow_steps` cites those gestures any
more, and the next pass read them again as new work -- every pass, for good.
One row per gesture a job has explained, whichever doing it came from.

Revision ID: 0071
Revises: 0070
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_placements",
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("gesture_id", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "gesture_id"),
    )


def downgrade() -> None:
    op.drop_table("workflow_placements")
