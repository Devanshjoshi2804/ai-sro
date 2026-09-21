"""a deployment learns its own writes

The gate that decides whether a step may be replayed as a call instead of
clicked reads one ledger: `knowledge-base/index/write-endpoints.json`, a
research project's hand-kept file. So a deployment that has watched its own
write succeed -- `Delete a Customer Type` ran eight times here, each one
confirmed by a read-back -- still clicked Save the ninth time.

Measured on this deployment 2026-09-21: 26 steps planned from evidence
against 162 planned by a model, and a run that replays its write as a call
performs 0.7 clicks against 1.5 and skips 4.1 steps as scaffolding.

This is where what a deployment watched is kept. Scoped to the tenant,
because a write verified against one customer's system is not verified
against another's.

Revision ID: 0068
Revises: 0067
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learned_writes",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("method", sa.String(16), primary_key=True),
        sa.Column("path_pattern", sa.Text, primary_key=True),
        sa.Column("origin", sa.Text, nullable=False, server_default=""),
        sa.Column("proved_by_run", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("verified_by", sa.String(16), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("learned_writes")
