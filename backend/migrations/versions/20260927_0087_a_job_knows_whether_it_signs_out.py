"""a job knows whether it signs out

`Log Out` was offered as work: nothing asked whether a job ends the session.
`workflows.signs_out` is the second chore verdict beside `signs_in`, decided by
code from the evidence. It is added NULL -- undecided -- on every stored job,
and each mining sweep decides every undecided job, both verdicts at once. The
downgrade drops the column; nothing older reads it.

Revision ID: 0087
Revises: 0085
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0087"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("signs_out", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflows", "signs_out")
