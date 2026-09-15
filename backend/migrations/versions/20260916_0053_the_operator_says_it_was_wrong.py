"""A run of a mined job carries what the operator said was wrong with it.

The ladder settles a step by what the warehouse answered and, where the
evidence records a read, by what that read showed. Neither can see a record
created exactly as asked that was not the record the person wanted -- a job
read out of a sentence can be the wrong job, and it answers 201 for it.

So the only witness is the person whose browser it ran in, and until now there
was nowhere to write down what they said. The column is what the report door
fills, and reading it back is how a reviewer finds the runs that looked clean
and were not.

Nullable with no default: null means nobody has reported this run, which is
almost every row and every row that existed before this migration.

Revision ID: 0053
Revises: 0052
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("wrong_because", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_runs", "wrong_because")
