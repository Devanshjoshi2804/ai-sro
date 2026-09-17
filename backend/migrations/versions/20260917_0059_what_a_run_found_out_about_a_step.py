"""What a run found out about a step, kept for the next one.

`workflow_stale` records that a step is about to break -- only the weakest rung
of the locator ladder could find its control. Nothing recorded what that rung
FOUND, so the discovery lived for exactly one command.

Measured on the deployment, 2026-09-17: `Create a Customer Type` step 2 clicks
a tab whose recorded identity matches nothing any more. Three runs in one
afternoon each paid for two model calls, each worked out that the control is
called "Customer Types", and each wrote it into a log line. At the end of the
afternoon the job knew what it knew at the start.

So a run writes down the locator that worked, and the next run tries it first.
Kept apart from the workflow for the same reason the stale table is: the
workflow is what a mining pass produces from evidence, this is what one run
observed, and one rewriting the other would race a re-mine.

Revision ID: 0059
Revises: 0058
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_learned",
        sa.Column("workflow_id", sa.String(64), primary_key=True),
        sa.Column("ord", sa.Integer(), primary_key=True),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("found_by", sa.Text(), nullable=False),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workflow_learned")
