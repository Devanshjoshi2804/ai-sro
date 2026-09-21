"""A run says what it is doing before it has a step to show for it.

Measured on the deployment 2026-09-16: an operator pressed "Yes, do it", the
card said "A run is performing here — Step 0" and stayed there for three and a
half minutes. The run was not stuck. It was reading their mailbox for the
values nobody had typed, and one round of that hit a 5xx from the model, which
the asker retried exactly as it should. Nothing anywhere said so.

Everything a run does is recorded as a STEP, and the gather is the one thing it
does before the first step exists. So one line on the row, written before the
looking starts and cleared when it ends -- what it is doing, in the words a
person watching would use.

Nullable and empty for every run before this, which is all of them: a row with
nothing in this column is a run that was never doing anything but its steps.

Revision ID: 0056
Revises: 0055
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("doing", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "doing")
