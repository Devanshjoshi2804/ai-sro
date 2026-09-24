"""A run keeps its progress on its row.

`workflow_runs` held no loop state: the step index, the lane and verdict per
step, the values read, the tab target ids and the writes made all lived in
the worker's memory, gone the moment the process was. A Steel run's progress
now lives on its row, so a worker restart resumes it and an API restart never
touches it.

`executor` says who is driving: `extension` (default, every existing run) or
`steel`, held to exactly those two values by `ck_workflow_runs_executor` --
without it a mistyped value (`"Extension"`, `""`) would sit outside every
narrowed rule below and never be swept. A Steel run has no device -- it lives
in the worker, not on anybody's press -- and may run beside others on one
tenant's account, so `uq_workflow_runs_one_running_per_device` is narrowed to
the runs it was ever about: `outcome = 'running' AND executor = 'extension'`.
The index is replaced, not dropped; no table or column is dropped.

`downgrade` recreates the wider index and cannot if two running Steel runs of
one tenant already share `device_id = ''` -- that state cannot exist before
this migration, so it only arises after Steel runs have been taken. It checks
for that first and refuses with a clear error rather than letting Postgres's
own duplicate-key error explain it.

Revision ID: 0073
Revises: 0072
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None

_ONE_RUNNING = "uq_workflow_runs_one_running_per_device"
_EXECUTOR_CHECK = "ck_workflow_runs_executor"


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("progress", JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("executor", sa.String(16), nullable=False, server_default="extension"),
    )
    op.create_check_constraint(
        _EXECUTOR_CHECK, "workflow_runs", "executor IN ('extension', 'steel')"
    )
    op.drop_index(_ONE_RUNNING, table_name="workflow_runs")
    op.create_index(
        _ONE_RUNNING,
        "workflow_runs",
        ["tenant_id", "device_id"],
        unique=True,
        postgresql_where=sa.text("outcome = 'running' AND executor = 'extension'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    clash = bind.execute(
        sa.text(
            "SELECT tenant_id, device_id FROM workflow_runs "
            "WHERE outcome = 'running' GROUP BY tenant_id, device_id HAVING COUNT(*) > 1"
        )
    ).first()
    if clash is not None:
        raise RuntimeError(
            "cannot downgrade 0073: tenant "
            f"{clash.tenant_id!r} has more than one running run with device_id "
            f"{clash.device_id!r} (a Steel run has none) -- the wider index this "
            "downgrade recreates cannot hold them both. Drain or fail those runs "
            "first."
        )
    op.drop_index(_ONE_RUNNING, table_name="workflow_runs")
    op.create_index(
        _ONE_RUNNING,
        "workflow_runs",
        ["tenant_id", "device_id"],
        unique=True,
        postgresql_where=sa.text("outcome = 'running'"),
    )
    op.drop_constraint(_EXECUTOR_CHECK, "workflow_runs", type_="check")
    op.drop_column("workflow_runs", "executor")
    op.drop_column("workflow_runs", "progress")
