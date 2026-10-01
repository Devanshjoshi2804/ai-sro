"""what went wrong in a chat is kept

`chat_feedback`: one row per (message, kind) of an objective signal that the brain or the old
chain got a turn wrong (an undo, a refused tool call, a failed run, a disagreement, a budget hit),
for a person to review and turn into eval cases. Nothing reads it to decide anything.

A new table: `create_table` and its indexes take locks on nothing that exists, so nothing waits on
them and `CONCURRENTLY` is not needed; no existing table is touched.

Revision ID: 0092
Revises: 0091
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0092"
down_revision = "0091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_feedback",
        sa.Column("id", sa.String(64), primary_key=True),
        # Arrival order, for "newest" when created_at ties (as `attempts` has it).
        sa.Column("seq", sa.BigInteger, sa.Identity(), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("thread_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("message_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("said", sa.Text, nullable=False, server_default=""),
        sa.Column("brain", JSONB, nullable=False, server_default="{}"),
        sa.Column("other", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # One row per (message, kind): a second signal of a kind on a message is the first's.
    op.create_index(
        "uq_chat_feedback_signal", "chat_feedback", ["tenant_id", "message_id", "kind"], unique=True
    )
    op.create_index("ix_chat_feedback_tenant_created", "chat_feedback", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("uq_chat_feedback_signal", table_name="chat_feedback")
    op.drop_index("ix_chat_feedback_tenant_created", table_name="chat_feedback")
    op.drop_table("chat_feedback")
