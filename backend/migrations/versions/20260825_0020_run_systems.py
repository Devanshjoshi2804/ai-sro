"""Every system a run touched, not only the one it is keyed by

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-25

A run is keyed by where the work lands, and a circuit breaker asks for the runs
of one system. That is exact while a run touches one system -- and a workflow
that adjusts the WMS and then records the receipt in the ERP is stored under the
WMS, so a failure in its ERP half was invisible to the ERP's breaker.

Asking every system a version touches, while only ever answering for one, is
half a breaker: it reads as protection and is not. This is the other half.

Empty for every run that already exists, which is what they were.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "systems",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "systems")
