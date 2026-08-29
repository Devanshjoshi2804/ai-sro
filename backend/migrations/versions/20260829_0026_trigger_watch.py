"""What makes a mail one the operator meant

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-29

A watch is a rule the operator's own browser holds and applies to a mail it
already has open. The rule still has to survive a laptop being closed, so it
lives here -- and what lives here is only ever the operator's own half of the
comparison: a sender they pointed at, a phrase from a subject, and the places
to read the task's parameters out of a matching mail.

No mail is stored, and there is no column one could reach. A term carries text
and names a header; a value carries a locator and no text at all. ADR 008 keeps
correspondence out of this system, and this column is shaped so that keeping it
out is not something somebody has to remember.

JSONB rather than three tables: a watch is read whole, by the one browser that
evaluates it, and never queried across.

Null for every trigger that already exists, which is every trigger that is not
a watch.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column("watch", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("triggers", "watch")
