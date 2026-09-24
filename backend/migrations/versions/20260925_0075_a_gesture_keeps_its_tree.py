"""a gesture keeps its tree

The accessibility tree taken before a gesture is stored with it, not
counted and dropped.

Revision ID: 0075
Revises: 0074
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gestures", sa.Column("tree", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("gestures", "tree")
