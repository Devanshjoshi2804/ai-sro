"""What the operator changed while a run was going

Revision ID: 0036
Revises: 0035
Create Date: 2026-09-03

The panel draws a run as it happens, a row per step, and a step that has not
been sent yet can still be argued with: the address was wrong, or the mail
never said which one. Changing it moves the value the later steps render from.

`parameters` alone would say what those steps used, but not that anybody chose
it. "Who decided this run would use A000221" is the first question asked about
a run that wrote the wrong record, so the change is recorded as well as
applied: name, value, and when, in the order they were made.

A document rather than a table. Nothing queries a revision -- they are read
beside the run they belong to, by somebody reading that run.

Empty for every run that already exists, which is what they are: nothing could
be changed mid-run before this.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "revisions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "revisions")
