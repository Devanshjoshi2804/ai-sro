"""a run keeps the version of its job it started with

`pinned` holds the job, its row and its steps' rows, as it stood when the run
started. Growing a job renumbers its steps; a run reads its pin instead,
so its `progress.step` and its marks keep meaning the steps they meant. Every
run still going is pinned to its job as it stands now, which is the version
it has been reading. Null on an extension run, which holds its job in memory.

Revision ID: 0082
Revises: 0081
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("pinned", JSONB, nullable=True))
    op.execute(
        """
        UPDATE workflow_runs AS run
        SET pinned = jsonb_build_object(
            'workflow', to_jsonb(job) - 'created_at' - 'retired_at',
            'steps', (
                SELECT coalesce(jsonb_agg(to_jsonb(step) ORDER BY step.ord), '[]'::jsonb)
                FROM workflow_steps AS step
                WHERE step.workflow_id = job.id
            )
        )
        FROM workflows AS job
        WHERE job.id = run.workflow_id AND run.outcome = 'running' AND run.executor = 'steel'
        """
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "pinned")
