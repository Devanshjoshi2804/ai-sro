"""A run that ended waiting to hear back from somebody outside this system.

`asking.py` already holds the good half: the state is the thread. A run that
comes up short ends, the question goes into the operator's own conversation
carrying everything established so far, and the answer may arrive days later
against a row rather than a process. Nothing is held open.

It has one address. The question is asked in the panel and answered in the
panel, and the person who knows the answer is very often not the person with
the panel open -- the mail asked for a customer type by description and named
no code, and the only one who can say what the code should be is whoever sent
it. Asking them means asking outside, and an answer that arrives outside has
to find its way back to the run waiting for it.

So a run may name the conversation it is waiting on: a connector and a thread
id, and the instant the waiting stops. The index is partial and expression-
based because the question asked of it is exactly one -- "is any run of this
tenant waiting on this thread" -- and it is asked of every arriving mail.

`until` is in the document rather than a column of its own: nothing sorts or
ranges over it, a reader of the row wants the whole wait, and a wait whose
deadline lived apart from its address could be stored without one.

Null on every run before this, and on every run nobody outside was asked
about, which is all of them so far.

Revision ID: 0062
Revises: 0061
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("awaiting", JSONB(), nullable=True))
    op.execute(
        """
        CREATE INDEX ix_workflow_runs_awaiting
            ON workflow_runs (
                tenant_id,
                (awaiting ->> 'server'),
                (awaiting ->> 'thread')
            )
            WHERE awaiting IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_awaiting", table_name="workflow_runs")
    op.drop_column("workflow_runs", "awaiting")
