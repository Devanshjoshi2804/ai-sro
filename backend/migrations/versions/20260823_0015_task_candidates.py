"""Tasks somebody keeps doing

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-23

A candidate is an episode class: the same piece of work, done more than once,
recognised by the calls it makes rather than by anything a person filled in.
Derived from evidence that is kept verbatim, so a better miner is re-run over
what is already stored rather than needing another week of watching.

The unique index is what makes re-running safe. Mining reads a window it has
read before, and the same task has to find its own row rather than becoming a
second candidate with a count of one.

`times_seen`, `first_seen` and `last_seen` are lifted out of the episode
document so "what did this person do most often" is an index rather than a scan
of every candidate's episodes.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_candidates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("host", sa.String(200), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("named_by_model", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("skill_id", sa.String(64)),
        sa.Column("dismissed_reason", sa.Text()),
        sa.Column(
            "episodes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("times_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_task_candidates_tenant_seen", "task_candidates", ["tenant_id", "times_seen"]
    )
    op.create_index(
        "uq_task_candidates_signature",
        "task_candidates",
        ["tenant_id", "principal_id", "signature"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_task_candidates_signature", table_name="task_candidates")
    op.drop_index("ix_task_candidates_tenant_seen", table_name="task_candidates")
    op.drop_table("task_candidates")
