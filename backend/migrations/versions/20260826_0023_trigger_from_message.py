"""Which values a message that fires a trigger may supply

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-26

A trigger is a button with its arguments already filled in, and that is what
makes a schedule safe to leave running: the same task, on the same thing, every
morning. A message names a different thing each time -- the order number in a
mail -- so some of its values have to come from whatever fired it.

Which ones has to be written down, because the alternative is a relay that can
name any parameter at all: post `facility=OTHER_DC` to a token you found in a
log, and a read somebody authorised for DC01 answers about another warehouse.
This column is the list of names that are the message's to fill; every other
value stays the one the trigger was created with.

Empty for every trigger that already exists, which is the behaviour they have
today.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "from_message",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("triggers", "from_message")
