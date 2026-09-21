"""A step names the earlier steps whose output it consumes.

CrewAI's `Task.context: list[Task]`, and its argument: a task that names the
prior tasks it depends on can be READ. One inspectable line answers "how does
step five get step two's id", where an implicit shared map means reading the
whole job and guessing.

Empty on every job mined so far, and honestly so. Measured on the deployment
2026-09-19: thirteen runs have made a record and not one has made two, so no
mined job has this shape and nothing emits the edge yet. The column is here
because composition is what needs it -- a person joining two jobs has to say
how the second gets the first's output -- and because the edge is discoverable
from evidence rather than guessed when mining comes to it: a value typed in
step five that equals what step two's response returned IS this edge, and the
recorded calls hold both halves.

Empty list and not null, like `cites` and `parameters` beside it: a step that
uses nothing uses nothing, and a nullable list is two ways to say so.

Revision ID: 0065
Revises: 0064
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("uses", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "uses")
