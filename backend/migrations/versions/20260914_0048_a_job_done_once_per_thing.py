"""A job can say which of its steps are done once per thing on a list.

"Add these three equipment types" is one job. Without this the rig could only
say it was a job that adds ONE, so a mail carrying three rows produced a run
that created the first and an operator did the other two by hand -- while
watching a browser that had just proved it could do them.

Two columns, both `jsonb`. `workflows.repeat` is nullable with no default. The pair of step numbers is one fact
and a row carrying one of them would mean nothing, which is the argument the
`arrival` column made one migration ago for the same shape. NULL is every job
mined before this and every job that does one thing once, which is most of
them.

No CHECK that `last_step >= first_step`: `Repeat.__post_init__` refuses that
where the refusal can say which end was wrong, and a constraint here would be
the same rule written twice in two languages.

Revision ID: 0048
Revises: 0047
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("repeat", postgresql.JSONB(), nullable=True))
    # And what a run's own steps say about which pass through the body they
    # were. `ord` stays what it was -- where in the run, unique within it,
    # which is what the key needs -- and these two say which step of the job
    # and which thing on the list, so a reader can tell the second pass from
    # the first without counting.
    op.add_column(
        "workflow_run_steps",
        sa.Column("of_step", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("workflow_run_steps", sa.Column("item", sa.Integer(), nullable=True))
    # And what one run was asked to do the body for. On the row because a
    # re-press carrying different items would finish a different job under this
    # run's id -- the same argument `from_step` made for its own column, and
    # the same check refuses it.
    op.add_column(
        "workflow_runs",
        sa.Column("items", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("workflow_run_steps", "item")
    op.drop_column("workflow_run_steps", "of_step")
    op.drop_column("workflow_runs", "items")
    op.drop_column("workflows", "repeat")
