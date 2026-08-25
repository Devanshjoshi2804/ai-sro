"""What a loop's body is being run with, once per thing in the list

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-26

A skill can now do part of its work once for each thing an earlier response
listed -- "adjust every short-shipped line on this order". How many times that
is, and which thing each time, is the system's own answer partway through the
run, so it is written down the moment it arrives.

On the run rather than recomputed, because a run that resumes after a restart
must do the iterations it started with. Re-reading the list would silently act
on whatever the warehouse says now, which is a different task with the same id.

Empty for every run that already exists, and for every run of a skill without
loops, which is nearly all of them.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "iterations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "iterations")
