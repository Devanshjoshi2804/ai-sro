"""a pool entry counts its unusable readings

`failed` is how many times an entry was shown to the model in a window whose
answer could not be used (it broke MINE's schema or was truncated). Such a
window is not mined, so it is read again; after K_MINE_ATTEMPTS it retires as
"unminable" rather than being billed on every pass. Zero for every earlier row.

Revision ID: 0083
Revises: 0082
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mining_pool",
        sa.Column("failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("mining_pool", "failed")
