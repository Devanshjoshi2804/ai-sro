"""Whether a run may take the operator's screen

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-25

A run performed in somebody's own Chrome can now bring a tab to the front, and
whether it may is the trigger's decision rather than the browser's: a task the
operator asked for and is watching may move their tab, and one a cron or a mail
relay started at 3am may not.

Carried on the run because a run outlives the request that started it -- the
step that would take focus may execute in a different process from the one that
decided it was allowed.

False for every run that already exists, which is what they were: until there
was an operator's browser to act in, there was no screen for a run to take.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("may_take_focus", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("runs", "may_take_focus")
