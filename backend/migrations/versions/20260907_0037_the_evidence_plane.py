"""The evidence plane

Revision ID: 0037
Revises: 0036
Create Date: 2026-09-07

Six tables for one thing: what a browser uploaded, what was read out of it, and
the evidence a mining pass could not place. `observation_batches` already
records that an upload arrived and points at the blob it landed in; this is the
correlated form -- one row per gesture, with the calls and page marks that
belong to it -- which is what a reading loop and a mining pass actually query.

`gesture_batches.batch_id` is minted by the extension and is the primary key,
which is the whole idempotence of ingest: an upload retried after its answer
was lost is refused rather than stored twice, and the second copy would double
every gesture in it and be mined as a second doing of the same job. Its
`started_at`/`ended_at` stay text: they are the device's own clock for the
window, kept exactly as it was sent, against `received_at`'s server clock.

`gestures.at` is a float of Unix seconds rather than a timestamp -- recorder.js's
own format, and what every ordering in the rig is on. Converting it would make
two formats for one number and a reading loop that sorts differently from the
browser that recorded it.

`orphan_pages` takes a bigserial `id`. In SQLite the rig used `INTEGER PRIMARY
KEY AUTOINCREMENT`, which is an alias for the implicit `rowid` Postgres has no
equivalent of, so the surrogate has to be declared. It stays a surrogate for
the reason it always was one: two distinct page events can share a batch, an
instant and a payload, and any natural key over those would silently drop the
second. Its sibling `orphan_requests` does have a natural key, `(batch_id,
request_id)`, so a replayed batch re-offers its orphaned calls without
doubling them.

`mining_pool` carries two counters because they measure opposite things and one
counter cannot be both. `age` counts readings an entry was shown and not cited
and runs out at K_POOL_AGE; `waited` counts passes it was passed over and
drives the priority that rotates the day. `retired` and `reason` are how an
entry stops being offered ahead of fresh evidence while staying in the store --
evidence that leaves the prompt without a record is the failure this
architecture exists to avoid.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gesture_batches",
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        # The device's own clock, kept as it was sent.
        sa.Column("started_at", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("ended_at", sa.String(length=64), nullable=False, server_default=""),
        # Which teaching recording a demonstration batch belongs to.
        sa.Column("recording_id", sa.String(length=64), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("batch_id"),
    )

    op.create_table(
        "gestures",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        # Unix seconds, float: recorder.js's own format.
        sa.Column("at", sa.Float(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("system", sa.Text(), nullable=True),  # scheme+host, derived at ingest
        sa.Column("tab_id", sa.Integer(), nullable=True),
        sa.Column("frame_url", sa.Text(), nullable=True),
        # The TAB's url, which is not the frame's: the address an operator
        # would type, and the one a run has to open.
        sa.Column("page_url", sa.Text(), nullable=True),
        sa.Column("gesture", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "requests",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "page_events",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gestures_tenant_at", "gestures", ["tenant_id", "at"])
    op.create_index("ix_gestures_stream", "gestures", ["tenant_id", "stream_id", "at"])

    op.create_table(
        "intents",
        sa.Column("gesture_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("act", sa.Text(), nullable=True),
        sa.Column("object", sa.Text(), nullable=True),
        sa.Column("system", sa.Text(), nullable=True),
        sa.Column("page", sa.Text(), nullable=True),
        sa.Column(
            "values_seen",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("continues", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Inside out_tokens, not beside it: thinking is billed at the output
        # rate. Its own column because on Flash it is ~84% of billed output,
        # and one number cannot tell a long answer from a long silence.
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        # A call that cost nothing and one whose cost could not be established
        # are the same row without this, and the bill is understated silently.
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Why it read nothing, when the API gave a reason.
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("gesture_id"),
    )
    # The spend sum reads it.
    op.create_index("ix_intents_tenant_created", "intents", ["tenant_id", "created_at"])

    op.create_table(
        "orphan_requests",
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("batch_id", "request_id"),
    )

    op.create_table(
        "orphan_pages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("at", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "mining_pool",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("gesture_id", sa.String(length=64), nullable=False),
        # Two clocks: `age` counts readings this entry was shown and not cited,
        # `waited` counts passes it was passed over. One counter cannot be
        # both -- using age for both made an entry read six times outrank one
        # never seen at all, and the day stopped rotating.
        sa.Column("age", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retired", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Why it retired, empty while it is still live.
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "gesture_id"),
    )


def downgrade() -> None:
    op.drop_table("mining_pool")
    op.drop_table("orphan_pages")
    op.drop_table("orphan_requests")
    op.drop_index("ix_intents_tenant_created", table_name="intents")
    op.drop_table("intents")
    op.drop_index("ix_gestures_stream", table_name="gestures")
    op.drop_index("ix_gestures_tenant_at", table_name="gestures")
    op.drop_table("gestures")
    op.drop_table("gesture_batches")
