"""What a browser proves it is itself with

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-29

Every device-scoped path is ``/v1/agents/{device_id}/...`` and the caller
authenticates with a tenant credential, which says which tenant is asking and
cannot say which browser. Until this column existed a device id was a namespace
rather than a credential: any extension holding a valid tenant token could list
another operator's mail rules and fire their watch into a live warehouse.

Minted at registration, held by that browser, presented on every device-scoped
call -- the shape a trigger's ``inbound_token`` already has, for a caller with
no principal behind it.

Null for every device registered before now. Such a device proves nothing and
is refused everywhere, which is the point: its extension is refused on its next
heartbeat, re-registers under the label it always used -- registration is
idempotent on (tenant, principal, label) -- and comes back as the same device
holding a secret. Backfilling one here instead would be a secret nobody could
tell the browser about, which is the same lockout with a value in the column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_devices", sa.Column("secret", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_devices", "secret")
