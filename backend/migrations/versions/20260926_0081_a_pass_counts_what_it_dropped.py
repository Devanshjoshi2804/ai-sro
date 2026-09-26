"""a pass counts what it dropped

`dropped` is how many proposed jobs per-item validation threw away for breaking
MINE's schema. Without it a pass whose every job was dropped reads as a day
with nothing in it. Zero for every earlier row: they were never counted.

Revision ID: 0081
Revises: 0080
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mining_passes",
        sa.Column("dropped", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("mining_passes", "dropped")
