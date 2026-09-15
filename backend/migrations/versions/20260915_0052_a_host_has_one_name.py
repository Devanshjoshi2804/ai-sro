"""A host has one name, and it is not the one the model made up that time.

`intents.system` was a free-text field on the per-gesture reading: one string
per gesture, asked of the model on the most-called path this system has, with
no description in the schema saying what it was for and nothing anywhere
reading it back.

It was noticed because it was visibly wrong. One warehouse host came back as
`Blue Yonder`, `BlueYonder`, `JDA WMS`, `WMS` and `WM` across the readings of a
single day -- five names for one origin, none of them agreeing, because nothing
had ever told the model what to write there and nothing checked what it did.

Removed rather than constrained. The miner never saw this: `as_evidence` shows
it `gesture.system`, the origin the browser actually recorded, which is exactly
one name per host by construction. The tail context shown to the next reading
is `one_line`, which is `act` and `object`. No route, no console screen and no
panel card reads the column. It was output tokens on every gesture, bought
nothing, and the only way anybody found out was that the values looked silly.

If a deployment ever wants a HUMAN name for a host -- "Blue Yonder" on a card
rather than `bf56-kms-wms-web-np2.jdadelivers.com` -- that is one row per host
somebody writes down once, in the knowledge base that already holds facts of
exactly that shape. It is not a sentence re-invented by a model fifty-five
times a day.

Revision ID: 0052
Revises: 0051
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("intents", "system")


def downgrade() -> None:
    # Null for every row. What it held was a model's guess at a name, and the
    # guesses disagreed with each other -- there is nothing to restore them
    # from and nothing that would read them if there were.
    op.add_column("intents", sa.Column("system", sa.Text(), nullable=True))
