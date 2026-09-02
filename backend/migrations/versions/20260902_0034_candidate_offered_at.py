"""When a candidate was offered to the operator

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-02

The offer -- "you've done this 3 times, about 51s each; want me to do the next
one?" -- used to be a card the panel drew from the candidate list. It appeared,
and when the panel closed it was gone. It is a message in the operator's thread
now, which means it is written rather than drawn: said once, and still there
tomorrow.

Written once is the whole difficulty. Mining sweeps run every quarter of an
hour over evidence they have already read, and without a record of having said
it, every sweep would post the same sentence again. A conversation that repeats
itself is one nobody reads.

Null for every candidate that already exists, which is honest: none of them
has been offered as a message, because until now there were no messages. Each
gets its sentence once, on the next sweep.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_candidates",
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("task_candidates", "offered_at")
