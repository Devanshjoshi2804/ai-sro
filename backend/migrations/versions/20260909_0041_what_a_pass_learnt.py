"""What a pass learnt, beside what it kept.

`MineResult` has counted `learned_parameters` since the miner was ported and
`mining_passes` had nowhere to put it, so the figure was computed once per pass
and discarded at the persistence layer. The rig has the same gap, so this is an
inherited hole rather than a port regression -- but it is the one number that
can say whether parameter learning is getting better, and a metric that does not
survive the pass computing it cannot answer that.

Measured on 2026-09-09: the second real pass over 507 real gestures learnt three
parameters -- `operationCode`, `longDescription`, `description`, each found by
diffing two doings of one job -- and the only place that number appeared was a
return value in a terminal. Nothing in the database said the pass had learnt
anything at all.

Backfilled to 0 rather than left null. A pass that ran before this column
existed learnt an unknown amount, and 0 is the honest floor: it is what every
row would have shown had the column been there and nothing been learnt. Null
would be the truer statement and would make the column awkward to sum, which is
the only thing anyone will do with it.

Revision ID: 0041
Revises: 0040
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mining_passes",
        sa.Column("learned_parameters", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("mining_passes", "learned_parameters")
