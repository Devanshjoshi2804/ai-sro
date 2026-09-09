"""Where a run was asked to start, beside what it was asked to do.

``run_workflow`` has taken ``from_step`` since the runner was ported and
``workflow_runs`` had nowhere to put it. It is not a progress marker the runner
advances: it is a request input naming how many steps the operator already
performed themselves before the offer was made, recorded ``done_by_operator``
and never sent -- the job is being finished, not redone.

The row a press writes is the authority for what that run is doing, and the
runner refuses a re-press whose ``device_id``, ``workflow_id`` or ``outcome``
disagrees with it. ``from_step`` is the fourth thing a press asks for and was
the only one of the four with no column to compare against, so a re-press
carrying a different one performed a different job under one run's id --
silently: steps redone against a live warehouse, or steps nobody did recorded
as done. This column is what lets that refusal be written.

Backfilled to 0, and here 0 is the true value rather than an honest floor for
an unknown. Every existing row was written by a system with no resume path at
all: nothing could pass a ``from_step`` through to storage, so every one of
those runs did begin at step zero. The backfill states a fact about them, not a
default standing in for one.

Revision ID: 0042
Revises: 0041
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("from_step", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "from_step")
