"""Workflows, the steps they cite, and the passes that found them

Revision ID: 0038
Revises: 0037
Create Date: 2026-09-07

Five tables between the evidence plane (0037) and the runs (0039): what a
mining pass found, the steps it cites, the weak steps a run noticed, and the
register of verified writes that buys a job the right to run unasked.

`mining_passes` rather than the rig's `passes`: the shorter word says nothing
about what kind of pass it is in a schema this size. It is the row that carries
a cost. A pass makes exactly one model call and proposes every workflow in it,
so a workflow names the pass rather than copying its bill -- three workflows
out of one $0.04 call summed to $0.12 when they each carried it, and the
overstatement grew with how well the pass did. A pass row is written whether it
found anything or not, including when the model refused, which is then the only
record left of a call that cost money and returned nothing.

`workflow_steps` carries no tenant and no foreign key, as in the rig: a step is
reached only through its workflow, which carries the tenant, and a workflow's
save deletes and reinserts its whole step set rather than appending -- which is
what makes a re-save of a merged workflow keep one copy of its steps and lose
a step the merge dropped.

`workflow_stale` is kept apart from the workflow itself because a mining pass
writes the workflow and a run writes this; rewriting the workflow from a run
would race a re-mine and lose one of the two. One row per step, so a job run
every morning reports the same weak step once rather than daily.

`workflow_effects` is keyed on (workflow_id, run_id, ord) and that composite
key IS the rule: one write of one run of one job is one effect however many
times it is verified. Only a state belt ever writes here -- never a picture, a
model reading a screenshot being no evidence that anything was written. Three
live held runs whose every write is in here is what buys a job the right to
write unasked, and one failed write empties it for that workflow.

Every clock is `timestamptz` where the rig kept text, as in 0039 and for the
same reason: both indexes here order on a clock, and an offset-less string
sorts beside an offset-bearing one with neither being wrong. The records still
carry ISO strings; the repository converts on both edges.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mining_passes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Inside out_tokens, not beside them.
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("proposed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kept", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("skew", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lopsided", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Why it found nothing, when it found nothing for a reason the API
        # gave. An honest zero and a refused call are the same row without it.
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mining_passes_tenant_started", "mining_passes", ["tenant_id", "started_at"])

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        # The pass that found it. Empty for a workflow saved outside a pass,
        # which today is only a test.
        sa.Column("pass_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("narrative", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "systems",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # What identity resolution compares a new proposal against.
        sa.Column(
            "shape_key",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # The model's opinion about whether this is one it has proposed before.
        # Recorded, and it decides nothing: a model re-judging its own earlier
        # verdict disagrees with itself at roughly 90%.
        sa.Column("same_as", sa.String(length=64), nullable=True),
        sa.Column(
            "unproven",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_tenant_created", "workflows", ["tenant_id", "created_at"])

    op.create_table(
        "workflow_steps",
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("says", sa.Text(), nullable=False, server_default=""),
        sa.Column("system", sa.Text(), nullable=True),
        # The gestures that prove the step. Free-generated workflow JSON
        # hallucinated up to 21% of steps; forced to select from real evidence
        # that fell below 7.5%, and an uncited step is a rejected step.
        sa.Column(
            "cites",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("workflow_id", "ord"),
    )

    op.create_table(
        "workflow_stale",
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("matched_by", sa.Text(), nullable=True),
        sa.Column("noticed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id", "ord"),
    )

    op.create_table(
        "workflow_effects",
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        # `status` or `read` and nothing else: the two verdicts that saw the
        # state itself.
        sa.Column("verified_by", sa.String(length=24), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id", "run_id", "ord"),
    )


def downgrade() -> None:
    op.drop_table("workflow_effects")
    op.drop_table("workflow_stale")
    op.drop_table("workflow_steps")
    op.drop_index("ix_workflows_tenant_created", table_name="workflows")
    op.drop_table("workflows")
    op.drop_index("ix_mining_passes_tenant_started", table_name="mining_passes")
    op.drop_table("mining_passes")
