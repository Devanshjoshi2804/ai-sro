"""sign-in pages are watched, structure-only

Spec §5.6. A stored policy whose exclusions equal, as a set, any default the
code ever wrote held that default, not a choice, so it becomes empty: the
8-host list 0022 left (fc5e8ed5's five plus the three mailboxes it appended),
the 9-host list 47672b14 wrote for new tenants, and the 3-host list b94e2830
did. Order is whatever wrote it, so it is compared as a set. Any other list is
the owner's and stays.

The version is bumped, the row's and the policy's own, as 0022 did: the
heartbeat sends a policy only when the version differs, and an extension that
is already signed in re-registers only when it is signed out -- without the
bump a healed row would never reach it.

There is no down: an identity provider going back to being excluded is not a
thing this migration should know how to do.

Revision ID: 0075
Revises: 0074
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0075"
down_revision: str | None = "0074"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_DEFAULTS = (
    frozenset(
        {
            "mail.google.com",
            "outlook.live.com",
            "mail.yahoo.com",
            "accounts.google.com",
            "login.microsoftonline.com",
            "outlook.office.com",
            "outlook.office365.com",
            "outlook.cloud.microsoft",
        }
    ),
    frozenset(
        {
            "mail.google.com",
            "outlook.live.com",
            "outlook.office.com",
            "outlook.office365.com",
            "outlook.cloud.microsoft",
            "mail.yahoo.com",
            "accounts.google.com",
            "login.microsoftonline.com",
            "b2clogin.com",
        }
    ),
    frozenset({"accounts.google.com", "login.microsoftonline.com", "b2clogin.com"}),
)


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT tenant_id, version, policy FROM observation_policies")
    ).all()

    for tenant_id, version, policy in rows:
        if frozenset(policy.get("exclude_hosts") or ()) not in OLD_DEFAULTS:
            continue
        changed = {**policy, "exclude_hosts": [], "version": version + 1}
        connection.execute(
            sa.text(
                "UPDATE observation_policies SET version = :version, policy = :policy "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id, "version": version + 1, "policy": json.dumps(changed)},
        )


def downgrade() -> None:
    """Nothing. An identity provider that is watched stays watched."""
