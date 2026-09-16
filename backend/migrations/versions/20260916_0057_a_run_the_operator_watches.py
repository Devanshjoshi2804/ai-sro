"""A run says whether somebody is watching it happen.

The system has two ways to do the same job and they are not interchangeable.
Replaying the call is fast, deterministic and invisible: the steps that only
put the form on the screen are skipped, and the record appears without anything
moving. Performing it is slower and costs a reading per step, and it is the one
an operator can watch -- the fields fill, the button is pressed, and a person
standing at the screen can see their job being done and stop it.

Until now the runner chose on its own, per step, and on 2026-09-16 it chose
both: it skipped the typing because it was going to post, then pressed Save as
if it had typed. The two are a decision about the whole run, and this is where
that decision is written down.

A press in an open panel means "show me". A trigger at three in the morning
means "just do it". False for every run before this, which is what they all
were.

Revision ID: 0057
Revises: 0056
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "watched")
