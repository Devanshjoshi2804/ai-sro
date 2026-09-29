"""a run knows the mail it came from

A run the mail door started held on Steel while the panel showed nothing that
said a mail had arrived. The run keeps the mail's envelope -- subject, sender,
conversation, when it arrived -- so the panel can say where it came from.
Never the body. NULL for every run no mail started.

Revision ID: 0090
Revises: 0089
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0090"
down_revision = "0089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("mail", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_runs", "mail")
