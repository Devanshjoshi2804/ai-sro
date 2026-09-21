"""A run says what the request asked for that the job cannot take.

A job's parameters are what two doings proved VARY. `Create a Customer Type`
declares two, because the two demonstrations differed in two fields and in
nothing else. The form has a dozen more -- Department, Manufacturer, Pallet
Building, Allocation Profile -- every one of them a perfectly ordinary thing
for somebody to ask for.

Ask for one, and until now the answer was a record without it and silence.
`keep` drops a name the job declares no parameter for, which is right: a run
that carried a field nothing demonstrated would be writing into a slot it
knows nothing about. Dropping it in silence is not right, and it is the shape
of every fault in this system worth having -- a request that asked for three
things, a record that holds two, and nothing anywhere naming the one that went
missing.

So the run keeps the names. Not the values: this column is read by a panel, a
log and whoever reviews the run, and what somebody wrote in their mail is
theirs. The names are enough to say "this job cannot take a Department yet",
which is the sentence a person needs in order to do the rest by hand or to ask
for the job to be taught again.

Empty for every run before this, which is the truth: nothing was recorded
about what they could not take.

Revision ID: 0060
Revises: 0059
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("unasked", JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "unasked")
