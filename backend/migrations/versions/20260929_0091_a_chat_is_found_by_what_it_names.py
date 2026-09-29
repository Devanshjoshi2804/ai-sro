"""a chat is found by what it names

`naming` (the chat that names a run, on every run announcement) and `holding`
(the chat holding a message) ask `messages @> ...`, which read every one of
the operator's threads' JSONB. A GIN index with `jsonb_path_ops` -- the
operator class built for `@>` alone, and the smaller one -- answers both.

Revision ID: 0091
Revises: 0090
"""

from __future__ import annotations

from alembic import op

revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_threads_messages",
        "threads",
        ["messages"],
        postgresql_using="gin",
        postgresql_ops={"messages": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_threads_messages", table_name="threads")
