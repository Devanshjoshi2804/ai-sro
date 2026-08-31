"""The sentence that started a run

Revision ID: 0033
Revises: 0032
Create Date: 2026-08-31

The one store for the sentence an operator typed to ask for a run: see
``Run.intent``'s docstring. Non-nullable with an empty default, because a
console run, a batch and a trigger never had a sentence to keep, and blank
already means "nobody typed one" everywhere else this pattern is used.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("intent", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("runs", "intent")
