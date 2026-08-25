"""What a candidate might be part of

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-25

Candidate identity is `(principal, signature)` compared for equality, which is
what keeps it stable across re-mining -- and what makes the same task done with
one extra page two candidates, and a task spanning two systems two candidates.

This is where a model is allowed to say so: a suggestion that two candidates are
one piece of work, with its reason, stored beside them. Nothing merges on it and
nothing downstream reads it. A person does.

Empty for everything that already exists, which is what they had: nothing had
been suggested about them.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_candidates",
        sa.Column(
            "joins",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("task_candidates", "joins")
