"""A run the person it ran for said was wrong

Revision ID: 0032
Revises: 0031
Create Date: 2026-08-31

`judge` reads statuses, media and escalations, and every one of them can be
clean while the record the run created is not the one anybody wanted. This is
where the only witness gets to say so.

Nullable, and null means nobody said anything -- which is the ordinary case and
is not a verdict. Nothing is asked after a run, so nothing goes unanswered.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("wrong_because", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "wrong_because")
