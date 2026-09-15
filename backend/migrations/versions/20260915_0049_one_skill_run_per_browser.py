"""One unfinished skill run per browser.

`workflow_runs` has had `uq_workflow_runs_one_running_per_device` since 0043,
and the reason it was written applies word for word to `runs`: reading "is this
browser busy" and then claiming it are two statements with awaits between them,
so two triggers firing at one device in the same minute both read free and both
claim -- two runs driving one window, interleaving their clicks into a form
neither of them can read back. The skill path had no guard of any kind, not
even the read.

Unlike 0043 this sweeps first. 0043 argued that no deployment could be holding
a duplicate pair and the argument had a hole in it -- the window where the
press door ran on 0041 and 0042 is exactly where duplicates came from. Arguing
is cheaper than sweeping and worse: an index that cannot be created leaves the
migration failed halfway through a deploy. Measured on this store before
writing it: no tenant holds a duplicate pair, so today the sweep ends nothing.

Revision ID: 0049
Revises: 0048
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The older of any pair, ended where it stands. A run still open on a
    # browser that has since driven another one is a run whose process is long
    # gone; `fail_orphans` is what would have ended it, and it only ever looked
    # at `workflow_runs`.
    op.execute(
        sa.text("""
        UPDATE runs SET ended_at = now(), status = 'failed',
               failure = 'ended by 0049: the browser had started another run'
        WHERE ended_at IS NULL AND device_id IS NOT NULL AND id NOT IN (
            SELECT DISTINCT ON (tenant_id, device_id) id FROM runs
            WHERE ended_at IS NULL AND device_id IS NOT NULL
            ORDER BY tenant_id, device_id, started_at DESC, id
        )
        """)
    )
    op.create_index(
        "uq_runs_one_running_per_device",
        "runs",
        ["tenant_id", "device_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    # The index goes; the runs this ended stay ended. Re-opening them would be
    # inventing a process to drive them.
    op.drop_index("uq_runs_one_running_per_device", table_name="runs")
