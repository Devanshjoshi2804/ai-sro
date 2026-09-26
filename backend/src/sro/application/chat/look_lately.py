from __future__ import annotations

import logging
from datetime import UTC, datetime

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.from_the_mail import FromTheMail, LookedInTheMail
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.chat.asking import Pending
from sro.domain.shared.identifiers import PrincipalId
from sro.whose import about

logger = logging.getLogger(__name__)

K_EVER = datetime(1970, 1, 1, tzinfo=UTC)


class LookInTheMailLately:
    def __init__(
        self, uow: UnitOfWork, look: FromTheMail, asks: AskAboutTheOffer, start: StartWorkflowRun
    ) -> None:
        self._uow = uow
        self._look = look
        self._asks = asks
        self._start = start

    async def execute(self) -> dict[str, LookedInTheMail]:
        async with self._uow as uow:
            operators = {
                tenant: sorted(
                    {
                        one.principal_id.value
                        for one in await uow.devices.list_for_tenant(tenant)
                        if not one.revoked
                    }
                )
                for tenant in await uow.gestures.tenants_since(K_EVER)
            }
        looked: dict[str, LookedInTheMail] = {}
        for tenant, principals in operators.items():
            for principal in principals:
                ctx = RequestContext(tenant_id=tenant, principal_id=PrincipalId(principal))
                if not self._start.runs_on_steel(ctx):
                    break
                with about(tenant=tenant.value, principal=principal):
                    try:
                        found = await self._look.execute(ctx)
                    except OverCap as reached:
                        logger.info(
                            "%s: the mail poll stopped at the cap -- %s", tenant.value, reached
                        )
                        break
                    for one in found.offered:
                        if not one.started:
                            await self._asks.execute(
                                ctx,
                                Pending(
                                    workflow_id=one.workflow_id,
                                    title=one.title,
                                    values=dict(one.values),
                                    missing=tuple(one.missing),
                                    limits=dict(one.too_long),
                                    mail_thread=one.thread,
                                ),
                                about=one.subject,
                                mail_thread=one.thread,
                            )
                looked[f"{tenant.value}/{principal}"] = found
        return looked
