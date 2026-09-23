"""a retired job stays retired

A job an operator retires leaves the known list, the offers and the runs, but
its row and its citations stay: the gestures it cites are still placed, so the
mining pass never reads them into a fresh copy of the job it was told to drop.
Null is a live job, which is every job stored before this.

Revision ID: 0070
Revises: 0069
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("workflows", "retired_at")
