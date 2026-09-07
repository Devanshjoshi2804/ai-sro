"""What a job's newest offers say about offering it again.

Ported from `counsel` in `new_agent_arch/src/rig/offers.py`. The rules are
`sro.domain.skill.offers.counsel_over`; the rows are `OfferRepository`'s two
windows. This is only the join -- and the join is where two of the three
things `counsel` actually promises live, because neither half can hold them:

* **`limit=K_WINDOW`.** The window's size is not a property of the rule. Half
  or more of *what* diverged is meaningless over a window of the wrong size:
  five diverged of ten moves the threshold and five of fourteen does not, so
  a caller reading a limit of its own choosing gets a different answer to the
  same question. The domain cannot enforce a size it is handed.
* **`limit=K_ENOUGH`.** `counsel_over` rests a job on `len(newest) ==
  K_ENOUGH` -- exactly that many, not at least -- precisely so that an uncut
  history cannot rest a job on evidence nobody scoped. That equality only
  means "the browser's newest three" if this is the caller that cut it to
  three.

The third promise is `record_offer`'s, next door.

`k > 0` is the repository's, not this function's: an arrival nudge is not
evidence either way, and keeping nudges out of the query is what lets the two
limits above mean what they say. A window of ten that a run of nudges could
fill is not a window of ten offers.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import K_ENOUGH, K_WINDOW, Counsel, OfferRow, counsel_over


async def counsel(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    workflow_id: str,
    device_id: DeviceId | None = None,
    now: datetime,
) -> Counsel:
    """The k this job should be offered at, and when this browser may see it.

    Two reads, because they are two questions. The threshold is a property of
    the job, so every browser's offers count towards it; the rest is a
    property of the pair, because one operator's no is not the next
    operator's. With no browser named there is nobody to rest, and the second
    read is not made at all rather than made and discarded.

    `uow` is already open and nothing here writes, so no commit: the caller
    owns the session.
    """
    window = await uow.offers.newest(tenant_id, workflow_id, limit=K_WINDOW)
    resting: tuple[OfferRow, ...] = ()
    if device_id is not None:
        resting = await uow.offers.newest_for_device(
            tenant_id, workflow_id, device_id, limit=K_ENOUGH
        )
    return counsel_over(window, resting, now)
