"""A counter that moves whenever a skill is written to

Revision ID: 0029
Revises: 0028
Create Date: 2026-08-30

Every version of a skill lives in one JSONB document, so two writers that both
read it, changed their own copy and saved overwrote each other. `latest_version`
was pressed into service as the optimistic-lock column because it already
existed and already counted -- but it only moves when a version is *appended*,
which left every other write racing.

The case that matters: two reviewers promoting two different versions of one
skill. Both rewrite the whole list, `latest_version` is the same in both, and
the second write silently undoes the first. The old comment called that correct
on the grounds that a stage is one field. It is not one field that gets
written; it is the document all the versions are in.

`revision` moves on every UPDATE and on nothing else, so the check covers
appends, promotions, demotions, track-record updates and repairs alike.

Starts at zero for every existing row, which is the same thing as no change:
the first write to each one reads zero, writes one, and the check has held from
then on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("skills", "revision")
