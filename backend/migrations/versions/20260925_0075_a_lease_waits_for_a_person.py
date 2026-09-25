"""a lease waits for a person

A sign-in that asks for a one-time code keeps its page open while a person
answers, so the lease gains a third live state, `waiting`. The one-live-lease
index is replaced to count it: a waiting lease still holds its account and its
browser context, and no second lease may be claimed beside it.

Revision ID: 0075
Revises: 0074
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def _one_live_lease(states: str) -> None:
    op.drop_index("uq_browser_sessions_one_live_lease", table_name="browser_sessions")
    op.create_index(
        "uq_browser_sessions_one_live_lease",
        "browser_sessions",
        ["tenant_id", "account_key"],
        unique=True,
        postgresql_where=sa.text(f"state IN ({states})"),
    )


def upgrade() -> None:
    _one_live_lease("'signing_in', 'ready', 'waiting'")


def downgrade() -> None:
    op.execute("UPDATE browser_sessions SET state = 'broken' WHERE state = 'waiting'")
    _one_live_lease("'signing_in', 'ready'")
