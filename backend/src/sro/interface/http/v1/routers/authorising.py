"""Who is on the record for a write, wherever one is authorised.

Two different things used to be one field. Whether somebody confirmed is the
operator's decision and stays in the request -- an assisted run with nobody
behind it is still refused. *Who* they are is not theirs to say: it comes from
the credential, so the name on a warehouse write is one this system checked
rather than one it was told.

Here rather than in one router because every rung that writes needs it: a
replay, a batch, and a pursuit working the task out on the screen.
"""

from __future__ import annotations

from sro.application.context import RequestContext


def authorising(confirmed: str | None, ctx: RequestContext) -> str | None:
    return ctx.principal_id.value if confirmed else None
