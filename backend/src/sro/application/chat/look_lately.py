from __future__ import annotations

import logging
from collections.abc import Sequence

from sro.application.chat.from_the_mail import FromTheMail, LookedInTheMail
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.whose import about

logger = logging.getLogger(__name__)


class LookInTheMailLately:
    def __init__(self, uow: UnitOfWork, look: FromTheMail, tenants: Sequence[str]) -> None:
        self._uow = uow
        self._look = look
        self._tenants = tuple(tenants)

    async def execute(self) -> dict[str, LookedInTheMail]:
        looked: dict[str, LookedInTheMail] = {}
        for tenant in map(TenantId, self._tenants):
            async with self._uow as uow:
                principals = sorted(
                    {
                        one.principal_id.value
                        for one in await uow.devices.list_for_tenant(tenant)
                        if not one.revoked
                    }
                )
            for principal in principals:
                ctx = RequestContext(tenant_id=tenant, principal_id=PrincipalId(principal))
                with about(tenant=tenant.value, principal=principal):
                    try:
                        looked[f"{tenant.value}/{principal}"] = await self._look.execute(ctx)
                    except OverCap as reached:
                        logger.info(
                            "%s: the mail poll stopped at the cap -- %s", tenant.value, reached
                        )
                        break
                    except Exception:
                        logger.exception(
                            "%s/%s: the mail poll could not look", tenant.value, principal
                        )
        return looked
