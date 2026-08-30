"""What has already been sent through a connector

Revision ID: 0030
Revises: 0029
Create Date: 2026-08-30

A network step is protected within its run: an answered write is never retried,
because a status code means the application saw it. Nothing protected a call
through a connector *across* runs -- the same trigger firing twice, a durable
workflow replayed after a crash, an operator pressing the button again because
the first press seemed to hang. For a mail that is one message becoming two,
and there is no taking it back.

The key is claimed by inserting it, before the call, and kept whatever the call
answers. A row rather than a list on something else, because two runs claiming
one key at the same moment is exactly the race this exists to lose, and a
primary key is the only thing that loses it reliably.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tool_calls",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("tool", sa.String(length=200), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("tool_calls")
