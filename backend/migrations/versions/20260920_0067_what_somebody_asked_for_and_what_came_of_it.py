"""Something a person asked this system for, and what came of it.

Everything here is recorded as STATE. A run is a row because a run was created,
an offer because an offer was made, an approval because somebody approved --
and `/v1/audit` reads a tenant's day by joining those four. It is a good
account of everything that worked.

Nothing at all is written when nothing happens. An operator presses "Yes, do
it" and a gate refuses before a run exists; they answer a question the thread
cannot use; they press Undo on a run with nothing to take back. The person
did something, the system decided, and the only trace is an HTTP status on a
request nobody kept -- so *I pressed it and nothing happened*, which is the
question support is actually asked, is unanswerable from anything stored.

Append-only, and never read by the runner: nothing in this system's behaviour
depends on a row here, which is what keeps it safe to write from a door that
is already refusing something.

Revision ID: 0067
Revises: 0066
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(64), primary_key=True),
        # The rig's `rowid` tiebreak made explicit, as `offers` has it: several
        # attempts share a second, and "newest" has to mean arrival order once
        # `at` ties -- Postgres promises no order at all without a column that
        # says so.
        sa.Column("seq", sa.BigInteger, sa.Identity(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("principal", sa.String(64), nullable=False, server_default=""),
        sa.Column("asked_for", sa.Text, nullable=False),
        sa.Column("came_of", sa.String(16), nullable=False),
        sa.Column("why", sa.Text, nullable=False, server_default=""),
        # The ids this was about -- run, workflow, thread, device, offer. A
        # column each would be a migration every time a door learns to name one
        # more thing, and none of them is ever joined on: this is read by
        # reading a tenant's day, in time order, and looking.
        sa.Column("about", JSONB, nullable=False, server_default="{}"),
    )
    # The only question this table is asked: what happened to this tenant,
    # since when. Newest first, which is how a day is read.
    op.create_index("ix_attempts_tenant_at", "attempts", ["tenant_id", "at"])


def downgrade() -> None:
    op.drop_index("ix_attempts_tenant_at", table_name="attempts")
    op.drop_table("attempts")
