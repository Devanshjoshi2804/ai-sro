"""A job is proven by what kept it, not by what the model said about the window.

`workflows.unproven` held what the mining pass could not place. The prompt asks
for that once -- "list anything you could not place" -- and the schema asked
for it per workflow, so the model attached the window's leftovers to whichever
job it happened to emit. Four readers then took it for a property of that job:
`serve_shapes` would not serve it, `create_trigger` would not schedule it,
`fire_trigger` skipped a schedule that existed, and the console's job list
filtered it out.

A real window always has leftovers -- a login, an inbox scrolled, a tab opened
and abandoned -- so the column was non-empty by construction and the whole
downstream was dead. On the first cross-tab evidence this system ever mined
from a real deployment, a correct six-step `Create a Customer Type` carried
thirty-six unplaced ids and was never offered. A third of those ids were
gestures supporting its own steps: the model cites about one gesture per step
and calls the rest unplaced, so the field was never "what you did that was not
this job" but "what I did not bother to cite".

The residue moves to the pass, which is whose fact it is. Nothing derives a
per-job replacement, because nothing needs one: `validate` already refuses a
workflow with an uncited step, an unknown gesture or a wordless one,
`work_only` refuses a stretch that is not work, and `undeliverable` strips a
parameter no step could be given. A workflow that was KEPT is the proven one --
that is what those checks mean, and the column was a second answer to a
question already answered.

Dropped rather than left empty. A column nothing writes and four things read is
the shape of this defect, and leaving it would leave the trap.

Revision ID: 0048
Revises: 0047
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("workflows", "unproven")
    # A count, beside `window_size` and `left_out`, which are the other two
    # figures about the reading rather than about what it found. Not the ids:
    # they are gesture rows this pass was shown and a reader can reach either
    # way, and thirty-six strings per pass is a paragraph on a row of numbers.
    op.add_column(
        "mining_passes",
        sa.Column("unplaced", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("mining_passes", "unplaced")
    # Empty for every row. What it used to hold was a fact about a window that
    # is not recoverable from a workflow, and inventing one per job is how the
    # confusion started.
    op.add_column(
        "workflows",
        sa.Column(
            "unproven",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
