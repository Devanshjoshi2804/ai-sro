"""One running run per browser, enforced rather than checked

Revision ID: 0043
Revises: 0042

Migration 0039 built ``ix_workflow_runs_tenant_device`` for the busy check and
wrote down what it was not: *"a read the caller acts on rather than a lock,
which is sound only while one worker owns every run; a second worker needs a
UNIQUE partial index on (tenant_id, device_id) WHERE outcome = 'running'."*

That was too generous, and this is that index. One worker is not enough.
``StartWorkflowRun.execute`` reads ``in_flight`` and then awaits twice more --
the workflow lookup and the save -- before the row exists, and every await is a
scheduling point on the one event loop. Two overlapping presses both read no
busy run and both claim the same browser: run against real Postgres with two
``asyncio.gather``ed presses, that produced two rows and zero refusals. A
double-click on a console button reaches it.

What that costs is the thing the busy check exists to prevent: two runs driving
the same window, interleaving their clicks into a form neither of them can then
read back, against a live warehouse.

Partial on ``outcome = 'running'``, so the constraint is exactly the rule and
not more than it: a browser may have any number of runs behind it and at most
one in flight. The read stays -- it is the friendly answer, it names the run
already driving, and it is what answers in the overwhelmingly common case where
there is no race at all. This is the backstop for the case the read cannot see,
and ``SqlWorkflowRunRepository.save`` turns the violation into the same
``Conflict``, in the same words, so a caller cannot tell which of the two
refused them.

No cleanup pass before the index is built, and that is a fact rather than an
optimism: nothing in ``src/`` wrote a ``workflow_runs`` row until the press
door landed, two commits ago. There is no deployment carrying a pair of running
runs for one browser, because there was no writer that could have made one.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "uq_workflow_runs_one_running_per_device"


def upgrade() -> None:
    op.create_index(
        _INDEX,
        "workflow_runs",
        ["tenant_id", "device_id"],
        unique=True,
        postgresql_where=sa.text("outcome = 'running'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="workflow_runs")
