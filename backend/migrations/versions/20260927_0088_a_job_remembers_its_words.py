"""a job remembers the operator's words for its fields

When a run asks which field a value belongs to and the operator picks one of
the form's labels, the wording the request used is kept against that job:
`(wording, field, role, confirmed_by, at)`, one per wording after
normalisation (`wording_key`), so a later answer replaces an earlier one. The
role is kept only when the form shows that label more than once, so the next
run can tell the two apart instead of asking again. Only an operator's answer
to the reader's own "which field" question writes here; a model never does.
Per job, never global.

Revision ID: 0088
Revises: 0085
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0088"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_aliases",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("workflow_id", sa.String(64), primary_key=True),
        sa.Column("wording_key", sa.Text(), primary_key=True),
        sa.Column("wording", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default=""),
        sa.Column("confirmed_by", sa.String(128), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("job_aliases")
