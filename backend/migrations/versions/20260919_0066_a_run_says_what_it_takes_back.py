"""A run says which run it takes back, where it is an undo of one.

The first place two jobs in this system are one piece of work. `21312266` gave
the result card an undo, and pressing it starts an ordinary run of an ordinary
mined job -- which is exactly right, and leaves the two with nothing between
them. The delete goes off on its own, and if it fails, the card that offered it
is gone and nobody knows the record is still there.

An id and not a status: whether the undo worked is the undo run's own outcome,
read where every other outcome is read. What this adds is only that the two can
be put side by side -- *this run took back run_abc* -- which is what a person
needs to see and what a second press has to be able to refuse.

Null on every run that is not an undo, which is all of them so far.

Revision ID: 0066
Revises: 0065
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("undoes_run", sa.String(64), nullable=True))
    # The one question this is asked: has this run been taken back already.
    # Without it, answering it means reading every run of the tenant.
    op.create_index("ix_workflow_runs_undoes", "workflow_runs", ["undoes_run"])


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_undoes", table_name="workflow_runs")
    op.drop_column("workflow_runs", "undoes_run")
