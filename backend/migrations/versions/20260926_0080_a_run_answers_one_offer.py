"""a run answers one offer

`offer` names the question (or mail) a run was started from. The partial
unique index makes a second start of the same offer -- a second panel, a
typed yes, the poll -- a refusal at the store rather than a second live write.
Null on every run started without one.

Revision ID: 0080
Revises: 0079
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("offer", sa.String(128), nullable=True))
    op.create_index(
        "uq_workflow_runs_one_per_offer",
        "workflow_runs",
        ["tenant_id", "offer"],
        unique=True,
        postgresql_where=sa.text("offer IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_workflow_runs_one_per_offer", table_name="workflow_runs")
    op.drop_column("workflow_runs", "offer")
