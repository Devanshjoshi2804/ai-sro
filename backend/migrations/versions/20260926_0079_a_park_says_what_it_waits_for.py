"""a park says what it waits for

A lease parked WAITING waits either for a one-time code typed on its page or
for a new password stored for its account. `waits_for` records which, so a
password answer ends only a password park and a code answer resumes only a
code park. Null on every lease that is not waiting.

Revision ID: 0079
Revises: 0077
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0079"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("browser_sessions", sa.Column("waits_for", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("browser_sessions", "waits_for")
