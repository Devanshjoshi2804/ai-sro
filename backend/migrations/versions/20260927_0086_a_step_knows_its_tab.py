"""a step knows its tab

Each step of a job acts in one tab of the run: `main`, a tab opened from
another role by a click (`opened_from:<role>`), or another tab the operator
opened on the same system (`tab_2`, ...). Learned by code at mining from the
gestures' tab ids and popup openers, and written on every new row. A step
stored before this was never judged, so its tab is NULL -- undecided -- and each
mining sweep decides it from the step's cited evidence, one step at a time,
only while it is still NULL. Readers take NULL as `main`.

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
    op.add_column("workflow_steps", sa.Column("tab", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_steps", "tab")
