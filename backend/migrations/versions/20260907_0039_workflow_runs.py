"""Workflow runs, their steps, and the approvals on them

Revision ID: 0039
Revises: 0038
Create Date: 2026-09-07

Three tables for one thing: what a run of a mined workflow did, and who said
yes to the writes in it.

`workflow_runs`, not `runs`. The backend already has a `runs` table for a
different concept and it predates this one, so the rig's table takes the
qualified name rather than the shorter one.

A run is written whole after every step -- the panel polls it while it is in
flight -- and `workflow_run_steps` is deleted and reinserted with it rather
than appended to, which is why a second save does not double the first step.
`workflow_run_steps` carries no tenant and no foreign key, as in the rig: a
step is reached only through its run, which carries the tenant.

`started_at` and `finished_at` are `timestamptz` where the rig kept text. Both
indexes order on `started_at`, and an offset-less string sorts beside an
offset-bearing one with neither being wrong. The records still carry ISO
strings; the repository converts on both edges.

The second index is the busy check: whether this browser already has a run in
flight. One browser, one hand -- two runs driving the same window interleave
their clicks into a form neither of them can then read back. It is a read the
caller acts on rather than a lock, which is sound only while one worker owns
every run; a second worker needs a UNIQUE partial index on (tenant_id,
device_id) WHERE outcome = 'running'.

That last sentence was too generous and migration 0043 is the correction: ONE
worker needs it too. The read and the claim are separated by awaits, so two
presses on one event loop both read free -- two rows, one browser, against real
Postgres. The index 0043 builds is the one named above; this one stays as what
it always was, the read that gives the friendly answer.

`approvals` is keyed on (run_id, ord) and that composite key IS the rule: the
first tap wins, and a second tap on the same step is not a second
authorisation. A write rescued to the second rung parks at the same step and
takes another tap; the first approver's browser is the one on the record. It
is not rewritten with the run, because the run record says a write went out
and this says a person let it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        # What this run is performed with. The press is the only source of
        # them: nothing a chat door understood is carried across on its own.
        sa.Column(
            # Quoted by hand: SQLAlchemy does not hold `values` to be reserved.
            sa.quoted_name("values", True),
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("started_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("live", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_focus", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False, server_default="running"),
        # The writes a dry run produced and did not send, in full. This is what
        # a person reads before pressing through to live.
        sa.Column(
            "withheld",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        # A run that cost nothing and a run whose cost could not be established
        # are the same row without this, and the bill is understated silently.
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_runs_tenant_workflow",
        "workflow_runs",
        ["tenant_id", "workflow_id", "started_at"],
    )
    # The busy check.
    op.create_index(
        "ix_workflow_runs_tenant_device", "workflow_runs", ["tenant_id", "device_id", "outcome"]
    )

    op.create_table(
        "workflow_run_steps",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("says", sa.Text(), nullable=False, server_default=""),
        sa.Column("planned_by", sa.Text(), nullable=True),
        # The command envelope's kind and payload.
        sa.Column("sent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # What the extension answered.
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verdict", sa.String(length=24), nullable=False),
        sa.Column("verdict_by", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("matched_by", sa.Text(), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("before_url", sa.Text(), nullable=True),
        sa.Column("after_url", sa.Text(), nullable=True),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("run_id", "ord"),
    )

    op.create_table(
        "approvals",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        # The browser whose panel the tap came from, when the panel named one.
        # A bare POST is a tap, so it is nullable.
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("run_id", "ord"),
    )


def downgrade() -> None:
    op.drop_table("approvals")
    op.drop_table("workflow_run_steps")
    op.drop_index("ix_workflow_runs_tenant_device", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_tenant_workflow", table_name="workflow_runs")
    op.drop_table("workflow_runs")
