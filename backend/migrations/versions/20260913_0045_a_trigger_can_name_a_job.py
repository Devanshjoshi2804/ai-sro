"""A trigger can name a mined job, not only a skill.

Until now nothing could start a rig workflow except a person accepting an
offer in the panel: `Trigger.skill_id` was a `SkillId`, so the scheduler and
the event dispatcher could only reach the pre-rig half of the system. A rig
job that has earned its autonomy -- three live held runs whose every write a
state belt verified -- still had to wait for a human to be looking at the
right tab at the right time.

Both columns become nullable and both tables gain `workflow_id`, because a
trigger names exactly one target and the domain enforces that invariant. A
CHECK constraint would say the same thing in the database; it is left out
deliberately. The rows already written all have a skill and no workflow, and
the invariant lives in `Trigger.__post_init__` where the refusal can say
which of the two was missing. A constraint here would only repeat it, and
SQLite (the test store) cannot add one to an existing table without a full
rebuild.

`confirmations` gets the same pair for the same reason: a trigger that
requires a person's say builds a card, and the card has to remember which
kind of thing it is asking about in order to start it.

Revision ID: 0045
Revises: 0044
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("triggers", "confirmations"):
        op.alter_column(table, "skill_id", existing_type=sa.String(64), nullable=True)
        op.add_column(table, sa.Column("workflow_id", sa.String(64), nullable=True))


def downgrade() -> None:
    """A trigger naming a job has no skill to fall back to, so it goes.

    Leaving it would make `skill_id` NOT NULL fail on the rows this feature
    created; there is no honest value to put in the column for them."""
    op.execute(sa.text("DELETE FROM triggers WHERE skill_id IS NULL"))
    op.execute(sa.text("DELETE FROM confirmations WHERE skill_id IS NULL"))
    for table in ("triggers", "confirmations"):
        op.drop_column(table, "workflow_id")
        op.alter_column(table, "skill_id", existing_type=sa.String(64), nullable=False)
