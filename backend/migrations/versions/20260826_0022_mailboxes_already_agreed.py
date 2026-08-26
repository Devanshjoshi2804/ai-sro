"""Corporate mailboxes are excluded from policies that already exist

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-26

`DEFAULT_EXCLUSIONS` gained the Microsoft 365 mailbox hosts, and a default only
ever reaches a tenant who has never had a policy. Every tenant already observing
kept the old five, so the fix reached nobody it was written for: a deployment
with capture on was recording `outlook.office.com` -- message bodies,
recipients, and a screenshot of the open message on every gesture -- for as long
as its retention window.

Appended rather than replaced, because the list is the tenant's: an exclusion
somebody added by hand must survive this. The version is bumped so that every
extension holding the old policy fetches the new one at its next heartbeat
rather than at its next restart.

There is no down: putting a mailbox back under observation is not a thing this
migration should know how to do.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MAILBOXES = ("outlook.office.com", "outlook.office365.com", "outlook.cloud.microsoft")


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT tenant_id, version, policy FROM observation_policies")
    ).all()

    for tenant_id, version, policy in rows:
        excluded = list(policy.get("exclude_hosts") or ())
        missing = [host for host in MAILBOXES if host not in excluded]
        if not missing:
            continue
        changed = dict(policy)
        changed["exclude_hosts"] = [*excluded, *missing]
        changed["version"] = version + 1
        connection.execute(
            sa.text(
                "UPDATE observation_policies SET version = :version, policy = :policy "
                "WHERE tenant_id = :tenant_id"
            ),
            {
                "tenant_id": tenant_id,
                "version": version + 1,
                "policy": json.dumps(changed),
            },
        )


def downgrade() -> None:
    """Nothing. A mailbox that stopped being observed stays that way."""
