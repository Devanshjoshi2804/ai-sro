"""sign-in pages are watched

A policy whose exclusions are exactly the old identity-provider default held
that default, not a choice, so it becomes empty. Any other list stays.

Revision ID: 0074
Revises: 0073
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

OLD_DEFAULT = ["accounts.google.com", "login.microsoftonline.com", "b2clogin.com"]


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE observation_policies SET policy = jsonb_set(policy, '{exclude_hosts}', "
            "'[]'::jsonb) WHERE policy -> 'exclude_hosts' = CAST(:old AS jsonb)"
        ).bindparams(old=json.dumps(OLD_DEFAULT))
    )


def downgrade() -> None:
    return None
