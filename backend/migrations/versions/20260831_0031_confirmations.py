"""Fires waiting for somebody to say yes

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-31

A manual trigger needs none of this: the click that fires it is the
confirmation. A schedule and an inbound message both go off with nobody there
to ask, so `CreateTrigger` refused to create one at all -- *a write has nowhere
to ask for confirmation yet: either set auto_approve, or start this one by
hand*.

This is the nowhere. The fire becomes a row, somebody answers it, and the run
starts then and with their name on it.

What it is not is a queue that drains itself. Nothing starts a run because time
passed; an unanswered row expires, and expiring is a decision to do nothing
rather than a decision deferred. `EXPIRED` is kept rather than deleted, because
"we chose not to" and "we never looked" are different things to read a month
later and only one of them is worth changing how a team works.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confirmations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("trigger_id", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=64), nullable=False),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("because", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.String(length=16), nullable=False, server_default="waiting"),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_by", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    # What the console asks for: this tenant's, waiting, oldest first.
    op.create_index(
        "ix_confirmations_tenant_answer",
        "confirmations",
        ["tenant_id", "answer", "asked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_confirmations_tenant_answer", table_name="confirmations")
    op.drop_table("confirmations")
