"""A mail relay's own way in

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-24

An inbound trigger has no principal on the other end of it -- an email or a
chat message carries no tenant credential. This is the secret it presents
instead: minted once at creation, checked in constant time, and the only thing
standing between a trigger id and a fire from outside.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("triggers", sa.Column("inbound_token", sa.String(64)))


def downgrade() -> None:
    op.drop_column("triggers", "inbound_token")
