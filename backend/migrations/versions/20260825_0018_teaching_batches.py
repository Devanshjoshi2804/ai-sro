"""A demonstration performed in the operator's own browser

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-25

Two halves of one thing. A recording can now say it was demonstrated in
somebody's own Chrome rather than in a browser this deployment opened -- which
is why it has no browser session, a state that until now read as a bug. And an
observation batch can say which demonstration it is part of, so teaching-mode
evidence can be told from an ordinary morning's browsing and assembled into
that recording's frames when it is sealed.

Both nullable, and null for everything that already exists: every recording so
far was driven server-side, and every batch so far was passive capture.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("recordings", sa.Column("device_id", sa.String(64), nullable=True))
    op.add_column("observation_batches", sa.Column("recording_id", sa.String(64), nullable=True))
    # Indexed because the one question asked of it is "everything belonging to
    # this demonstration", asked once per seal.
    op.create_index(
        "ix_observation_batches_recording",
        "observation_batches",
        ["recording_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_observation_batches_recording", table_name="observation_batches")
    op.drop_column("observation_batches", "recording_id")
    op.drop_column("recordings", "device_id")
