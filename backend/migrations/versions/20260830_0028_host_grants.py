"""Pages an operator said may be watched after all

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-30

The exclusion list is what a tenant agreed to by default: webmail and sign-in
pages are never observed, because continuous capture of somebody's mailbox is
what needs a DPIA and what employee consent cannot make lawful. The cost of
that default is that the mail half of a task could never be demonstrated at
all -- press teach in a mailbox and the recording came back empty.

A grant is the operator saying otherwise about one page, in their own browser,
for the tab in front of them, visible in the panel while it lasts and revoked
when they close the tab. Not monitoring somebody; somebody showing you
something.

Held on the device rather than on the tenant, because that is what it is: one
person's decision about one of their own tabs. Every grant carries an expiry,
so a browser that stopped without revoking cannot leave a mailbox standing
open, and grants widen ``exclude_hosts`` only -- an administrator who named the
only hosts that may ever be observed made a decision an operator does not get
to overrule from a side panel.

Empty for every existing device, which is the same thing as no change: a device
that has granted nothing is observed exactly as it was yesterday.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_devices",
        sa.Column(
            "grants",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_devices", "grants")
