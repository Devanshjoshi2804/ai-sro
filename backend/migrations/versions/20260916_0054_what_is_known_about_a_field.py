"""A step carries what is already known about the values it is about to write.

The one failure the ladder cannot see is a record created exactly as asked that
is not the record the operator wanted, and the sharpest instance of it is a
value the field is too small to hold: the form sends `ZV9680`, the column keeps
`ZV96`, and the warehouse answers 201 for it.

Somebody already wrote that down -- the knowledge base carries 404 `field`
claims read off the system's own documentation, and `customerType`'s says
`max_length: 60`. This column is where the answer is put so the person who taps
Approve sees it beside the write.

A list of sentences rather than structured rows: what is stored is what a card
shows, and a reader of this table should not have to render anything.

Revision ID: 0054
Revises: 0053
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_run_steps",
        sa.Column(
            "notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_run_steps", "notes")
