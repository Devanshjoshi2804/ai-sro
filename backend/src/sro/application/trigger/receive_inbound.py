from __future__ import annotations

import hmac
from collections.abc import Mapping

from sro.application.ports.repositories import UnitOfWork
from sro.application.trigger.fire_trigger import Fired, FireTrigger
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import TriggerId
from sro.domain.trigger.trigger import TriggerKind


class InboundRefused(DomainError):
    code = "inbound_refused"


class ReceiveInbound:
    def __init__(self, uow: UnitOfWork, fire: FireTrigger) -> None:
        self._uow = uow
        self._fire = fire

    async def execute(
        self, trigger_id: TriggerId, *, token: str, message: Mapping[str, str] | None = None
    ) -> Fired:
        async with self._uow as uow:
            trigger = await uow.triggers.find(trigger_id)
        if (
            trigger is None
            or trigger.kind is not TriggerKind.INBOUND
            or trigger.inbound_token is None
            or not hmac.compare_digest(trigger.inbound_token.encode(), token.encode())
        ):
            raise InboundRefused("no such inbound trigger")
        return await self._fire.execute(trigger_id, message=message)
