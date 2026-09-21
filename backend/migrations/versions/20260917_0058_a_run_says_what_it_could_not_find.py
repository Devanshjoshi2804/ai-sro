"""A run says what it could not find, so somebody can be asked.

The run goes and looks for whatever nobody typed -- in the mail that asked for
the job, and in time in the systems themselves. When the looking comes back
short the run has to end: a write with a blank in it is a wrong record, and a
warehouse record cannot be un-created.

Until now that was the end of the whole thing. The row said "nobody gave a
value for Customer Type, and your mail does not say either", and an operator
who had already pressed yes started over from the offer.

The names are what turns that dead end into a question. The run keeps them,
and the panel takes the conversation from there: one question per value, in
the operator's own thread, in words -- and when the last answer lands the job
runs with the full set on the yes they already gave.

Empty for every run before this, which is the truth: they found everything or
they stopped.

Revision ID: 0058
Revises: 0057
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("needs", JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "needs")
