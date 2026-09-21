"""What a job taught itself, kept rather than overwritten.

`workflow_learned` is one row per step and the last answer wins. That is right
for the question it answers -- what should the next run try first -- and it
means a job rewrites its own behaviour with nothing left behind. A locator that
was learned from a screenshot and quietly replaced a locator that was learned
from a component is a job that drifted, and the only record of it is the
difference between two runs nobody compared.

So every change is appended here first: what the step used to be, what it
became, which run taught it, and when. Append-only and never updated -- a
history that can be edited is a history nobody can rely on -- and read by
nobody in the hot path, so a job that has learned four hundred times costs a
run nothing.

Only CHANGES. A run that found the same locator as the run before it has
taught nothing, and a row per confirmation would bury the four that matter
under four hundred that do not.

Revision ID: 0064
Revises: 0063
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_learned_history",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        # `locator` or `holds`. Named rather than split into two tables: they
        # are the same event -- a job changed its mind about a step -- and a
        # reader wants them in one order.
        sa.Column("about", sa.Text(), nullable=False),
        # What it was, and what it became. Text for both, including the limit:
        # the reader is a person, and "4" beside "60" says what an integer
        # column and a nullable one would say less clearly.
        sa.Column("was", sa.Text(), nullable=False, server_default=""),
        sa.Column("now", sa.Text(), nullable=False, server_default=""),
        # Which run taught it, so somebody reading a surprising locator can go
        # and look at the run that found it, the rung that produced it, and the
        # screen it was standing on.
        sa.Column("by_run", sa.String(64), nullable=False, server_default=""),
        sa.Column("found_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    # The one query this table is for: what has this job taught itself, newest
    # first. A history nobody can read in one page is a log.
    op.create_index(
        "ix_workflow_learned_history_job",
        "workflow_learned_history",
        ["workflow_id", "at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_learned_history_job", table_name="workflow_learned_history")
    op.drop_table("workflow_learned_history")
