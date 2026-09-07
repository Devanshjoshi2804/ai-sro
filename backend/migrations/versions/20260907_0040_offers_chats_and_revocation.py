"""Offers, chats, and taking a browser's authority away

Revision ID: 0040
Revises: 0039
Create Date: 2026-09-07

Two tables and one column, and all three are about what a browser did.

`offers` is every offer the extension made from a recognised prefix and what
became of it -- the labelled record of whether recognition was right. `seq` is
the one thing the rig's SQLite gave for free: it ordered ties on `rowid`, and
Postgres promises no order at all for two rows that tie. They do tie, routinely:
the extension sends whole-second ISO instants and a job can be offered several
times in one second. The newest three of a browser's offers decide whether the
job is rested for a day, so "newest" has to mean arrival order once `at` ties --
hence an identity column, which is what `rowid` was.

`at` is `timestamptz` where the rig kept text. The index orders on it and an
offset-less string sorts beside an offset-bearing one with neither being wrong.
The records still carry ISO strings; the repository converts on both edges.

`chats` is one row per sentence the chat door read, with what the reading cost.
There is no column for the sentence and that is the design: it is an operator's
words about their own warehouse, and the row exists for the cap and the spend
line, neither of which needs them. The index is `(tenant_id, at)` because the
day's spend is a sum over exactly that.

`agent_devices.revoked_at` is how a browser stops speaking for itself. The rig
had a `device_tokens` table with its own bearer per browser; the backend already
mints `agent_devices.secret` and the extension already sends it, so only the
revocation travels. A column rather than a deleted row, and the secret is left
alone rather than blanked: a device with no secret cannot be told from one
registered before secrets existed, and an audit of what a browser was allowed to
do needs the instant its authority ended. Nothing in this plan refuses a revoked
device -- that is the auth dependency -- but this is what it will read.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.String(length=64), nullable=False),
        # The rig's `rowid`, made explicit. See the note above: it breaks the
        # tie on `at`, and the tie is what decides whether a job is rested.
        sa.Column("seq", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        # How many gestures of the tail matched when it was offered. Zero is an
        # arrival nudge -- "you have been here before", nothing typed -- which
        # is neither kind of evidence and is filtered out of the window.
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("fate", sa.String(length=16), nullable=False),
        # The run an accepted offer started, and nothing for the other four.
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offers_tenant_workflow", "offers", ["tenant_id", "workflow_id", "at"])

    op.create_table(
        "chats",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        # The job the sentence turned out to be about, when it was about one.
        sa.Column("workflow_id", sa.String(length=64), nullable=True),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Inside out_tokens, not beside them.
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        # A reading that cost nothing and a reading nobody could price are the
        # same row without this, and the day's bill is understated silently.
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # The day's sum reads this.
    op.create_index("ix_chats_tenant_at", "chats", ["tenant_id", "at"])

    op.add_column(
        "agent_devices", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("agent_devices", "revoked_at")
    op.drop_index("ix_chats_tenant_at", table_name="chats")
    op.drop_table("chats")
    op.drop_index("ix_offers_tenant_workflow", table_name="offers")
    op.drop_table("offers")
