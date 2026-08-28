"""Which induction rules made the last learning attempt

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-28

0024 stopped the sweep retrying evidence it had already refused, by writing
down how many doings the last attempt saw. That asks one question -- "is there
new evidence?" -- where there are two. The other is "can this system do
something today that it could not do when it last tried?"

It could not, and then it could: a candidate refused because two of its doings
differed, several defects in induction were fixed, and the same stored evidence
became learnable -- but nothing retried it, because no new doing had arrived.
It sat refused in front of an operator while the code that would have learned
it was already merged. Nobody would ever have found out.

So the attempt is stamped with the version of the rules that made it, and a
fresh attempt is worth making when either has moved.

Zero for every candidate that already exists, deliberately. The tidy default
would be the current version -- assume what is stored was tried by today's
rules -- and it would be wrong for every row in the table: their attempts were
made by rules nobody was counting, which is exactly the situation this exists
to fix. Zero says so honestly, and buys each of them one attempt under rules
that have changed several times since. One attempt per waiting candidate is the
whole cost; the cost of the tidy default is that the candidates this was built
for are the ones it skips.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_candidates",
        sa.Column("learned_under", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("task_candidates", "learned_under")
