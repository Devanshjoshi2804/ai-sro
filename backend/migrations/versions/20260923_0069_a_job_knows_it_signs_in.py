"""a job knows it signs in

A run used to guess whether the job it was running signs in, from every cited
gesture being on one origin -- which is also every ordinary job done on one
warehouse host, so a run that lost its page was reported as succeeded with
its steps undone. Whether a job signs in is decided once, by the mining pass,
from what the operator did: a credential typed and nothing written back. Jobs
already stored are false until the healing pass reads their evidence.

Revision ID: 0069
Revises: 0068
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("signs_in", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("workflows", "signs_in")
