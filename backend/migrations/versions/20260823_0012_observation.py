"""Devices, observation batches and the policy that permits them

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-23

An extension in the operator's own browser uploads what they did. Three tables,
and the shape of them is the argument.

A device is a row because an administrator answering "whose browsers are being
observed" needs a list, and because a command channel has to address one. Unique
on (tenant, principal, label) so a reinstalled extension re-registers as itself
rather than as a second device.

A batch is a row that points at an object. The events are millions a day and
none of them is fetched by id -- they are read whole, over a window, by a miner.
In a column the row that says "this arrived" would cost as much to read as the
evidence it points at.

The policy is a row per tenant, and its absence is a refusal. Passive
observation of every tab an operator opens is monitoring; ADR 008 makes it a
contract conversation rather than a default, so a tenant nobody has configured
captures nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("extension_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paused_by", sa.String(64)),
        sa.Column("queued_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploads", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_agent_devices_tenant_seen", "agent_devices", ["tenant_id", "last_seen_at"])
    op.create_index(
        "uq_agent_devices_tenant_principal_label",
        "agent_devices",
        ["tenant_id", "principal_id", "label"],
        unique=True,
    )

    op.create_table(
        "observation_batches",
        # The extension's own id, primary key on its own: a retried upload must
        # be recognised as the same batch rather than counted twice, and
        # counting how often something happened is the miner's whole job.
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("principal_id", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("byte_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "rejected",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index(
        "ix_observation_batches_tenant_started",
        "observation_batches",
        ["tenant_id", "started_at"],
    )
    op.create_index(
        "ix_observation_batches_principal",
        "observation_batches",
        ["tenant_id", "principal_id", "started_at"],
    )

    op.create_table(
        "observation_policies",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_table("observation_policies")
    op.drop_index("ix_observation_batches_principal", table_name="observation_batches")
    op.drop_index("ix_observation_batches_tenant_started", table_name="observation_batches")
    op.drop_table("observation_batches")
    op.drop_index("uq_agent_devices_tenant_principal_label", table_name="agent_devices")
    op.drop_index("ix_agent_devices_tenant_seen", table_name="agent_devices")
    op.drop_table("agent_devices")
