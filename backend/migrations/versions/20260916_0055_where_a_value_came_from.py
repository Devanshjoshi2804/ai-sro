"""A run says where its values came from, for the ones nobody typed.

A value the operator typed into the press needs no provenance: they were
standing there and they meant it. A value read out of a mailbox is only as good
as the message it came from -- and the one failure the ladder cannot see is a
record created exactly as asked that was not the record anybody wanted.

So the message id and the span it was quoted from are kept beside the run, and
the person approving the write can go and read the mail.

Empty for every run whose values came from a person, which is all of them
before this.

Revision ID: 0055
Revises: 0054
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "gathered",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "gathered")
