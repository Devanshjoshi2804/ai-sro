"""A run says whether it has already written to whoever asked.

The panel's question works because somebody is standing in front of it. The
case this is for is the one where nobody is: a request naming a description
and no code, a mailbox that does not say either, and an asker who is not the
operator, is not watching a panel, and may be in another country.

So the run writes to them -- drafted, read by the operator, and sent only on a
press. This column is what stops it writing twice.

A counter in the process would not do. A worker that restarted between one
stop and the next would buy somebody a second mail about one request, and a
mail cannot be unsent: it is the least reversible thing this system does, it
leaves the company over the operator's name, and the person receiving two of
them learns that this system is noise.

False on every run before this, which is the truth: none of them asked
anybody.

Revision ID: 0063
Revises: 0062
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "asked_the_asker",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "asked_the_asker")
