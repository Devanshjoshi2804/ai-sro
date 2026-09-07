"""What a tenant's day of model calls may cost before the rig stops asking.

The rule is the rig's ``over_cap`` in ``new_agent_arch/src/rig/api.py``, and
the number it judges comes from ``SpendRepository.today`` -- four billable
tables summed since midnight UTC, with the blind rows counted beside the sum.
This file judges; it queries nothing itself.

Three things about the rule, each of them a decision rather than an accident:

* **A cap that stops the ASKING is honest in a way a cap that stopped capture
  would not be.** Evidence still arrives and is still stored, so raising the
  cap tomorrow reads what today declined. Over the cap, the mining pass, the
  chat door and a new run answer 429 with the sentence returned here, and the
  reading loop simply does not ask.
* **A negative cap means no cap**, which is what a deliberate one-off
  measurement wants -- and it is answered before the repository is touched, so
  the measurement does not pay for a query it has already opted out of. **Zero
  disables the asking entirely**: nothing has been spent, and zero is still
  reached.
* **A day whose cost cannot be trusted is not a cheap day.** ``blind`` stops
  the day just as hard as the dollars do, because a model name the price table
  never knew about records $0.0000 with ``unpriced`` set: an unattended week on
  a new preview name spends without limit while a guard reading ``cost_usd``
  alone reads zero. This deployment lived that once -- the run that proved the
  architecture billed $1.12 and every row said free.

The rig's ``SPENT_IN`` has no counterpart here on purpose. It is the list of
tables, clock columns and blind-row predicates that ``spent_today`` queried
with, and plan 2 landed it as ``_BILLED`` in
``sro/infrastructure/db/spend.py``, where the schema it names lives. The
application layer may not import infrastructure, and a second copy of that
table over here would be a second answer to "what bills" -- which is the exact
failure its docstring is about.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend


async def spent_today(uow: UnitOfWork, tenant_id: TenantId, *, now: datetime) -> DaySpend:
    """The dollars and the blind calls this tenant has run up since midnight.

    A delegation, kept because the rule below and every caller that reports the
    day's bill want one name for it, and because ``now`` travelling this far is
    what lets a caller's clock -- not the server's -- decide which day is being
    asked about.
    """
    return await uow.spend.today(tenant_id, now=now)


async def over_cap(
    uow: UnitOfWork, tenant_id: TenantId, *, now: datetime, cap_usd: float
) -> str | None:
    """Why the rig will not make another model call today, or ``None``.

    The sentence is the one a 429 carries and the log keeps: how much of what,
    so whoever reads it knows whether to raise the cap or to go and find the
    unpriced call.
    """
    if cap_usd < 0:
        return None
    day = await spent_today(uow, tenant_id, now=now)
    # `>=`, not `>`: a cap is the amount that may be spent, so the day that
    # spent exactly it has spent it. And `or day.blind`, because cost_usd
    # alone cannot tell an honestly-cheap day from one whose bills were never
    # priced -- the reason says both numbers so a reader can tell which stopped
    # the day.
    if day.cost_usd >= cap_usd or day.blind:
        return (
            f"daily cap reached: ${day.cost_usd:.4f} of ${cap_usd:.2f} spent today,"
            f" {day.blind} unpriced call(s)"
        )
    return None
