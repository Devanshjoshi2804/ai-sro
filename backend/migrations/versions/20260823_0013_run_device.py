"""Which browser a run was performed in, when it was not one of ours

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-23

A run can now be performed in the operator's own Chrome, through the extension,
instead of in a browser this deployment owns. Which one it was is the first
question anybody asks about a run that touched the wrong record, so it is
recorded on the run rather than resolved again at each step -- a device chosen
fresh per step could answer that question differently every time.

Nullable, and null for every run that already exists: they were all performed
server-side, and that is what null means here.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("device_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "device_id")
