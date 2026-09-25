"""a lane known broken

A lane that failed a step is remembered per tenant, job, step and lane, with a
fingerprint of how it failed and the step's `cites` key at the time, so the
next run skips it; a new doing of the job changes the key and clears it.

Revision ID: 0076
Revises: 0075
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "known_broken",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("workflow_id", sa.String(64), primary_key=True),
        sa.Column("ord", sa.Integer(), primary_key=True),
        sa.Column("lane", sa.String(8), primary_key=True),
        sa.Column("fingerprint", sa.String(32), primary_key=True),
        sa.Column("cites", sa.String(32), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_known_broken_job", "known_broken", ["tenant_id", "workflow_id"])


def downgrade() -> None:
    op.drop_table("known_broken")
