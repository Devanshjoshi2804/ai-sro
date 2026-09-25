"""a job not yet judged is undecided

0069 added `workflows.signs_in` as NOT NULL DEFAULT false, so every job
stored before it read as "decided: does not sign in", and the flag was only
ever evaluated when new gestures arrived. On a quiet system nothing arrived,
nothing was decided, and the vault key migration found no sign-in job to
move. NULL now means undecided: every stored false is reset to it (true only
ever came from evidence, so it is kept), new rows start as it, and each mining sweep decides every undecided job from its
evidence. The downgrade maps NULL back to the false the older code expects.

Revision ID: 0078
Revises: 0077
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("workflows", "signs_in", nullable=True, server_default=None)
    op.execute("UPDATE workflows SET signs_in = NULL WHERE signs_in = false")


def downgrade() -> None:
    op.execute("UPDATE workflows SET signs_in = false WHERE signs_in IS NULL")
    op.alter_column("workflows", "signs_in", nullable=False, server_default=sa.false())
