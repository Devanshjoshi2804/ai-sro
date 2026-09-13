"""How big a pass's window was, and how much it could not hold.

`MineResult` has counted `window_size` and `left_out` since the miner was
ported and `mining_passes` had nowhere to put either, so both were computed
once per pass and discarded at the persistence layer -- the same hole migration
0041 closed for `learned_parameters`, in the same table, for the same reason.

Closed now because a sweep needs them. `worker.mine_the_rig_lately` reads and
mines every recorded tenant on the hour, and a tenant whose evidence has not
changed since its last pass would otherwise be re-read every hour forever: one
measured pass over tenant `new` cost $0.34, proposed the two jobs it already
knew, kept nothing, and would have done exactly that twenty-four times a day.

What stops that from being simply "skip a tenant with no new evidence" is the
pool. A day too big for one window is read across several passes -- ten
simulated passes went 81% then 96%, with nineteen gestures never shown -- so a
pass that LEFT SOMETHING OUT has more to say about evidence that has not
changed, and a pass whose window held everything does not. `left_out` is that
distinction and nothing persisted it.

Backfilled to 0 rather than left null, the same reading 0041 made: a pass that
ran before these columns existed had an unknown window, and 0 is the honest
floor for what it left out. It also makes the backfilled rows say "this pass
held everything", which is the conservative direction here -- it can cost a
sweep that should have run, never a spend that should not have happened.

Revision ID: 0044
Revises: 0043
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mining_passes",
        sa.Column("window_size", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "mining_passes",
        sa.Column("left_out", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("mining_passes", "left_out")
    op.drop_column("mining_passes", "window_size")
