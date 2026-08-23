"""What starts a run when nobody typed a sentence

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-23

Until now every run began with a request somebody made. A trigger is the record
that says a task runs on a clock, with these values, in this browser -- and, for
anything that changes a system, with a named human's standing authorisation.

That column is the reason this is a table rather than a cron file. A scheduled
write happens with nobody watching, and `Run` refuses an above-shadow write with
no authoriser; storing the authorisation here means the refusal happens when the
trigger is created, which is hours or weeks before the first time it would have
gone off with nobody's name on it.

`writes` is copied from the skill at creation for the same reason a run copies
its stage: a skill re-induced into something that writes must not silently turn
an old read-only trigger into a writing one.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "triggers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("skill_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("cron", sa.String(120)),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("device_id", sa.String(64)),
        sa.Column("medium", sa.String(16), nullable=False, server_default="network"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("writes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authorized_by", sa.String(64)),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("may_take_focus", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_fired_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_id", sa.String(64)),
        sa.Column("disabled_reason", sa.Text()),
    )
    op.create_index("ix_triggers_tenant_created", "triggers", ["tenant_id", "created_at"])
    op.create_index("ix_triggers_tenant_skill", "triggers", ["tenant_id", "skill_id"])


def downgrade() -> None:
    op.drop_index("ix_triggers_tenant_skill", table_name="triggers")
    op.drop_index("ix_triggers_tenant_created", table_name="triggers")
    op.drop_table("triggers")
