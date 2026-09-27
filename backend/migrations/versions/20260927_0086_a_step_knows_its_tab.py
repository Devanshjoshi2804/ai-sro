"""a step knows its tab

Each step of a job acts in one tab of the run: `main`, a tab opened from
another role by a click (`opened_from:<role>`), or another tab the operator
opened (`tab_2`, ...). Learned by code at mining from the gestures' tab ids and
popup openers. Every existing step was mined as one tab, so it defaults `main`.

Revision ID: 0086
Revises: 0085
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_steps", sa.Column("tab", sa.Text(), nullable=False, server_default="main")
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "tab")
