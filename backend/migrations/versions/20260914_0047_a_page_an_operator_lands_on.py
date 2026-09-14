"""A trigger can be a page the operator arrives on.

The wire that was missing. This system could recognise a job and could drive a
browser through one, and the only things that joined them were a person
pressing a button, a console, and a clock -- so an operator watching their own
browser be driven through a login asked why it could not do that by itself.

One column, `jsonb`, beside `watch` and for the same reason it is beside it:
both are rules a browser holds and applies locally, and neither type has a
field the other's data would fit in. A watch carries terms about a mail; an
arrival carries one page, as `host/path`. There is nowhere in either for the
other's content, which is the guard rather than a rule somebody remembers.

Nullable with no default, like `watch`: the kind is what says which of them a
row is, and `Trigger.__post_init__` refuses a row whose kind and fields
disagree -- where the refusal can say which field was wrong. A CHECK here
would be that rule written twice in two languages.

Revision ID: 0047
Revises: 0046
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("triggers", sa.Column("arrival", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    """A trigger that fires on a page has no other way to fire, so it goes.

    Left in place with the column gone it would be an arrival-kind row with no
    page: `Trigger` refuses to build one, so every read of that tenant's
    triggers would raise instead of answering."""
    op.execute(sa.text("DELETE FROM triggers WHERE kind = 'arrival'"))
    op.drop_column("triggers", "arrival")
