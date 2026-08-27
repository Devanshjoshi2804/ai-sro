"""How many doings learning was last tried on

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-27

A task done often enough is now taught with nobody pressing anything, on the
same sweep that notices it. Where its evidence will not induce -- two doings
that are not two doings of one task -- the honest answer is to wait for a
better pair, and the candidate stays where an operator can see it.

But the sweep comes round every quarter of an hour, and without this it tried
the same unchanged evidence again every time, sealing two more recordings on
each pass. This is how many doings had been seen at the last attempt: a fresh
attempt is worth making when there is something new to make it on.

Zero for every candidate that already exists, which means each gets exactly one
attempt on the evidence it already has.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_candidates",
        sa.Column("learned_from", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("task_candidates", "learned_from")
