"""The page a task starts on

Revision ID: 0035
Revises: 0034
Create Date: 2026-09-03

A candidate now remembers where its first doing began -- host and path of the
first page a gesture was seen on, without the query string.

It is what lets the panel say "you have done this here before, shall I do it?"
the moment somebody lands on that page, instead of waiting to be asked. The
recognition has to happen in the browser, on every navigation, against a list
the extension already holds; a column is what makes that a comparison rather
than a request.

Without the query, because that is where a warehouse system puts session ids
and timestamps: a page addressed with one is never the same page twice, and a
page that is never the same page twice is one nothing can recognise.

Empty for every candidate that already exists. That is honest rather than
convenient -- none of them recorded a starting page, and guessing one from the
host would nudge on every screen of the application. Each fills in on its next
doing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_candidates",
        sa.Column("starts_on", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("task_candidates", "starts_on")
