"""a job knows which parameters rule it was given

Since M3 every value a job types is a parameter unless a doing proves it
constant, and code decides it rather than a model. Jobs stored before that
were decided the old way; the sweep brings each in once. This is the version
of the rule last applied to the job, NULL for never, so "once" survives a
restart and a later rule can bring every job in again.

Revision ID: 0089
Revises: 0086
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0089"
down_revision = "0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("parameters_rule", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflows", "parameters_rule")
