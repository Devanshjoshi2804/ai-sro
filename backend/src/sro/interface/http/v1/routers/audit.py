"""Everything a person would want to see after the fact, since a time.

Ported from `new_agent_arch/src/rig/api.py:1366`. Tenant-only, as it is there:
the runs every browser started, the offers every browser answered and the bill
the chat door ran up are the tenant's to read, and a browser's secret opens its
own doors and not the other browsers' evidence.

Two divergences from the rig, both deliberate:

`since` is required. The rig defaulted it to `""`, which meant everything ever;
plan 3b made the call at the use-case level -- `ReadAudit.execute` takes a
`datetime` with no default -- and this route keeps it. An unbounded audit over a
real tenant is a table scan nobody meant to ask for, and every caller that has a
reason to be here has a window in hand already.

A `since` that cannot be read is a 422 naming the parameter, where the rig
raised its own 400. Same rule underneath -- an audit must not answer "nothing
happened" to a time it could not parse -- said by FastAPI's own validation
rather than by a hand-written branch, which is the one place it could drift from
what the generated client believes.

Nothing here catches a domain error: `sro.interface.http.errors` maps them once,
for every route.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import AuditResponse

router = APIRouter(tags=["audit"], dependencies=[TenantOnly])


@router.get("/audit")
async def audit(
    container: ContainerDep,
    ctx: ContextDep,
    since: Annotated[datetime, Query()],
) -> AuditResponse:
    """The runs, the offers, the browsers and the chat readings since a time.

    The `since` that comes back is the use case's, never this parameter: a
    naive time is read as UTC one layer down, and a caller has to be able to
    tell which instant they were actually given.
    """
    return AuditResponse.of(await container.read_audit().execute(ctx, since=since))
