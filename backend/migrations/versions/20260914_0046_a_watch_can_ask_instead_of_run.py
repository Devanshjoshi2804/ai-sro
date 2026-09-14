"""A watch can ask a question instead of running a job.

A mail arrives saying "how many suppliers are set up at SG". The answer is in
the systems the operator works in, and there is no job for a trigger to name:
`umbrella` is explicit that looking something up is a step of a job and never
a job, so the miner will never produce one. Until now every trigger had to
name a skill or a workflow, which meant a mail that asked a question could
only be turned into an offer to run something -- or ignored.

One boolean, and the invariant that reads it lives in `Trigger.__post_init__`
where the refusal can say which of the three cases is wrong. No CHECK
constraint here, for 0045's reason and one more: the rule is now
three-branched (a skill, a job, or a question and neither), and a constraint
repeating it in SQL is a second place for it to disagree with itself.

Nothing about what a watch MATCHES changes, and nothing about what leaves the
browser does. The question is a value -- a location in the mail, read at match
time, passed as a parameter, never written down -- which is the same contract
every other value read out of a mail is already under. ADR 008's line is where
it was.

Revision ID: 0046
Revises: 0045
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column("asks", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """A trigger that asks names no skill and no job, so it goes.

    Left in place it would be a row the domain refuses to build: the moment
    the column is gone, `asks` reads false and `Trigger` sees a trigger that
    runs neither of the two things it can run."""
    op.execute(sa.text("DELETE FROM triggers WHERE asks"))
    op.drop_column("triggers", "asks")
