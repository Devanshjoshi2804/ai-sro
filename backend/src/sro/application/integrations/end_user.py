from __future__ import annotations

from sro.application.context import RequestContext
from sro.domain.shared.errors import InvariantViolation


def end_user_id(ctx: RequestContext) -> str:
    if ":" in ctx.tenant_id.value or ":" in ctx.principal_id.value:
        raise InvariantViolation("A tenant or principal id with ':' cannot be told apart in Nango")
    return f"{ctx.tenant_id.value}:{ctx.principal_id.value}"
