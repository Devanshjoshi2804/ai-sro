"""A recording names its objective at seal, not at start

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("objective_type", 64),
    ("target_system", 64),
    ("entity_type", 64),
    ("facility", 64),
    ("direction", 16),
)


def upgrade() -> None:
    for column, length in _COLUMNS:
        op.alter_column("recordings", column, existing_type=sa.String(length), nullable=True)


def downgrade() -> None:
    # Recordings still capturing have no objective yet and cannot be given one
    # here; they are abandoned rather than guessed at.
    op.execute("DELETE FROM recordings WHERE objective_type IS NULL")
    for column, length in _COLUMNS:
        op.alter_column("recordings", column, existing_type=sa.String(length), nullable=False)
