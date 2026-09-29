"""a learned locator keeps its frame

A locator the sight lane learned was found in a frame, and the next run must
look for it in that frame: `workflow_learned.frame_path` holds the hops the
hit test answered, as JSON text. Null for a locator learned without one.

Revision ID: 0077
Revises: 0076
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_learned", sa.Column("frame_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_learned", "frame_path")
