"""The day's bill, summed over every table that can bill it.

The rule is the rig's ``spent_today`` and its ``SPENT_IN`` table, in
``new_agent_arch/src/rig/api.py``: four tables, each with its own clock column
and its own idea of what a blind row is, summed since midnight UTC. What the
rig learnt the expensive way is in that table's docstring and is the reason
this file exists rather than one ``SUM`` in a use case -- a cap that summed one
of the four was a cap on a quarter of the bill.

Two things are carried across unchanged and are worth saying out loud.

* **The blind count is read beside the sum, not derived from it.** A model name
  the price table never heard of records ``cost_usd`` 0.0 with ``unpriced``
  set, so a day read on ``cost_usd`` alone spends without limit while the guard
  reads zero. The measurement run that proved this architecture billed $1.12
  and every row said free.
* **A call that errored is unpriced without being blind.** Nothing was billed,
  so the price is not unknown -- it is nil, and a 503 at breakfast must not
  lock the day. ``workflow_runs`` is the exception, because a run carries no
  error column: its blind row is the one that billed nothing at all, which is
  the shape of the accident this exists for. A run that billed its other steps
  and lost one step to a 503 is not that.

What ``over_cap`` does with the pair is a pure rule and lives in the
application layer. This produces the numbers; it judges none of them.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import SpendRepository
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend
from sro.infrastructure.db.models import ChatRow, IntentRow, MiningPassRow, WorkflowRunRow

_BILLED = (
    (
        IntentRow.tenant_id,
        IntentRow.cost_usd,
        IntentRow.created_at,
        and_(IntentRow.unpriced, IntentRow.error.is_(None)),
    ),
    (
        MiningPassRow.tenant_id,
        MiningPassRow.cost_usd,
        MiningPassRow.started_at,
        and_(MiningPassRow.unpriced, MiningPassRow.error.is_(None)),
    ),
    (
        WorkflowRunRow.tenant_id,
        WorkflowRunRow.cost_usd,
        WorkflowRunRow.started_at,
        and_(WorkflowRunRow.unpriced, WorkflowRunRow.cost_usd == 0.0),
    ),
    (
        ChatRow.tenant_id,
        ChatRow.cost_usd,
        ChatRow.at,
        and_(ChatRow.unpriced, ChatRow.error.is_(None)),
    ),
)
"""Every table a model call bills to: whose it is, what it cost, the column
that says when, and what a blind row is there. The rig's ``SPENT_IN``, with
``passes`` and ``runs`` under the names this schema gives them and each clock
column its own -- they are not all called the same thing, and reading three of
them off one name is how a table falls quietly out of the sum."""


class SqlSpendRepository(SpendRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        # UTC when the caller's clock said nothing, and midnight is UTC's
        # either way: a naive `now` read as the server's local time moves the
        # boundary by the machine's offset, which on a westward host bills
        # yesterday evening to today and hands a fresh day a spent cap.
        aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        midnight = aware.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        usd, blind = 0.0, 0
        # ponytail: four round trips, as the rig made four queries. One
        # UNION ALL if the cap check ever shows up in a profile -- it runs
        # once per model call, which costs seconds.
        for tenant_column, cost, clock, blind_is in _BILLED:
            # COALESCE because SUM over no rows is NULL, and a quiet morning
            # must read as $0.00 rather than crash the guard that reads it.
            # COUNT needs no such help; over no rows it is 0.
            spent = (
                await self._session.execute(
                    select(func.coalesce(func.sum(cost), 0.0), func.count().filter(blind_is)).where(
                        tenant_column == tenant_id.value, clock >= midnight
                    )
                )
            ).one()
            usd, blind = usd + float(spent[0]), blind + int(spent[1])
        return DaySpend(cost_usd=usd, blind=blind)
