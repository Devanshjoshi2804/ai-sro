"""a job keeps the recipients its operator named

A mail job may write only to the conversation it answers and to the addresses
its own demonstration sent to. Anybody else is a question to the operator, and
their answer -- an address, from the panel or from their own mailbox -- is kept
here per job, with who named it and when, so the next run does not ask again.
Only that answer writes a row; a model never does.

Revision ID: 0085
Revises: 0083
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0085"
down_revision = "0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_recipients",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("workflow_id", sa.String(64), primary_key=True),
        sa.Column("address", sa.String(320), primary_key=True),
        sa.Column("confirmed_by", sa.String(128), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("job_recipients")
