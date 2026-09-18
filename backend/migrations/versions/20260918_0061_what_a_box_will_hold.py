"""What a box will hold, learnt once and kept.

A field truncates in the browser, silently and before the request. Measured on
this deployment and written down in the knowledge base before the rig ever hit
it: `Warehouse.Description` stops at about 28 characters with no error and no
warning. The run now catches that at the moment it types, because that is the
only moment the difference between what was asked for and what the box will
take exists.

Catching it every time is repeating, not learning. `learned_step.py` says what
that costs, about locators:

    three runs in one afternoon paid for two model calls each, worked out that
    the control is called "Customer Types", and wrote it into a log line. At
    the end of the afternoon the job knew exactly what it knew at the start.
    That is not a system that learns -- it is one that repeats.

The same table, the same shape, the same rule: one row per step, the last
answer winning. A run that discovers the limit writes it here, and the next run
of that job knows before it opens a form -- so it stops before filling half of
one, and in time asks for a shorter value at the moment somebody is deciding
rather than in the middle of a job.

Null on every row learnt before this, and on every step that is not a typing
step, which is the truth: nothing has been observed about what those boxes
hold.

Revision ID: 0061
Revises: 0060
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_learned", sa.Column("holds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_learned", "holds")
