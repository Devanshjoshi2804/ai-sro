"""a session is leased

`browser_sessions` gains the lease fields (§5.2): who it is for, where it
lives, and how long it has left. A unique partial index allows one live
lease per account, live meaning `state IN ('signing_in', 'ready')` -- a
row with no state is still an ordinary capture session, so the index never
touches one.

Revision ID: 0073
Revises: 0072
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("browser_sessions", sa.Column("origin", sa.Text(), nullable=True))
    op.add_column("browser_sessions", sa.Column("username", sa.Text(), nullable=True))
    op.add_column("browser_sessions", sa.Column("container_url", sa.Text(), nullable=True))
    op.add_column("browser_sessions", sa.Column("steel_session_id", sa.String(128), nullable=True))
    op.add_column("browser_sessions", sa.Column("context_id", sa.String(128), nullable=True))
    op.add_column("browser_sessions", sa.Column("holder", sa.String(128), nullable=True))
    op.add_column(
        "browser_sessions",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "browser_sessions", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("browser_sessions", sa.Column("state", sa.String(16), nullable=True))
    op.create_index(
        "uq_browser_sessions_one_live_lease",
        "browser_sessions",
        ["tenant_id", "origin", "username"],
        unique=True,
        postgresql_where=sa.text("state IN ('signing_in', 'ready')"),
    )


def downgrade() -> None:
    op.drop_index("uq_browser_sessions_one_live_lease", table_name="browser_sessions")
    op.drop_column("browser_sessions", "state")
    op.drop_column("browser_sessions", "expires_at")
    op.drop_column("browser_sessions", "heartbeat_at")
    op.drop_column("browser_sessions", "holder")
    op.drop_column("browser_sessions", "context_id")
    op.drop_column("browser_sessions", "steel_session_id")
    op.drop_column("browser_sessions", "container_url")
    op.drop_column("browser_sessions", "username")
    op.drop_column("browser_sessions", "origin")
