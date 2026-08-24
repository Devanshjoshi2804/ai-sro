"""A mail relay or a chat webhook, asking for its trigger to fire.

There is no principal on the other end of an email -- no bearer token, no
tenant to prove by reading a row the caller's own credential unlocked. The
per-trigger token is the only thing standing in for that, so it is checked in
constant time and a wrong trigger id and a wrong token look identical from the
outside: neither should tell an unauthenticated caller which one it got wrong.
"""

from __future__ import annotations

import hmac

from sro.application.ports.repositories import UnitOfWork
from sro.application.trigger.fire_trigger import Fired, FireTrigger
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import TriggerId
from sro.domain.trigger.trigger import TriggerKind


class InboundRefused(DomainError):
    """No such reachable inbound trigger. Deliberately the same error whether
    the id is wrong, the kind is wrong, or the token is wrong."""

    code = "inbound_refused"


class ReceiveInbound:
    def __init__(self, uow: UnitOfWork, fire: FireTrigger) -> None:
        self._uow = uow
        self._fire = fire

    async def execute(self, trigger_id: TriggerId, *, token: str) -> Fired:
        async with self._uow as uow:
            trigger = await uow.triggers.find(trigger_id)
        if (
            trigger is None
            or trigger.kind is not TriggerKind.INBOUND
            or trigger.inbound_token is None
            or not hmac.compare_digest(trigger.inbound_token, token)
        ):
            raise InboundRefused("no such inbound trigger")
        return await self._fire.execute(trigger_id)
