"""every model call is billed

One row per call the model answered, whichever adapter made it and whatever
the caller did with the answer. The day's spend and the cap are summed here,
and only here.

Revision ID: 0072
Revises: 0071
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_spend",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("in_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("out_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unpriced", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_model_spend_tenant_at", "model_spend", ["tenant_id", "at"])


def downgrade() -> None:
    op.drop_index("ix_model_spend_tenant_at", table_name="model_spend")
    op.drop_table("model_spend")
