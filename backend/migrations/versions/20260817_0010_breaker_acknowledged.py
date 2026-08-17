"""A tripped breaker a person can close again

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-17

The breaker says "a person should look before anything else is sent" and gave
that person nothing to do about it. Every run against the system was refused
until the window aged out, including the run that would have shown the problem
was already fixed.

So the acknowledgement is recorded: who looked, when, and why they decided it
was safe to carry on. Failures before that moment stop counting; the breaker is
closed by a named decision rather than by waiting.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "connections",
        sa.Column("failures_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("connections", sa.Column("acknowledged_by", sa.String(255), nullable=True))
    op.add_column("connections", sa.Column("acknowledgement_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("connections", "acknowledgement_reason")
    op.drop_column("connections", "acknowledged_by")
    op.drop_column("connections", "failures_acknowledged_at")
