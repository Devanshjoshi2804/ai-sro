from __future__ import annotations

from sro.application.context import RequestContext


def end_user_id(ctx: RequestContext) -> str:
    return f"{ctx.tenant_id.value}:{ctx.principal_id.value}"
