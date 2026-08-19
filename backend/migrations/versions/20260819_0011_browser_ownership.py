"""Which tenant a browser session belongs to

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-19

A browser session id was a bare string. Nothing said who opened it, so six code
paths took one from a URL, from the provider's list of live sessions, or from a
query parameter, and then drove it or emptied its cookies into the caller's
vault -- none of them able to tell one customer's browser from another's.

Ownership cannot live in memory: the API and the Temporal worker each build
their own container, and both open, enumerate and close browsers. A claim only
one process can see is the reason the stray sweep waits a quarter of an hour
before it dares release anything.

The provider is left out of it. Steel has no tenants and must not learn about
any; this is a fact this system records about an id it was handed back.

Sessions open at the moment this is deployed have no row, so the sweep releases
them. That is correct rather than unfortunate: an unowned browser is exactly
what this table exists to stop.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        # The provider's own id, primary key on its own: a session belongs to
        # exactly one tenant, so a second claim is a conflict rather than a
        # second row. That constraint is the whole security property.
        sa.Column("session_id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("opened_by", sa.String(64), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_browser_sessions_tenant", "browser_sessions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_browser_sessions_tenant", table_name="browser_sessions")
    op.drop_table("browser_sessions")
