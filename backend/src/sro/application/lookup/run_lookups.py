from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.execution.answer import Answer, read_answer
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.repositories import UnitOfWork
from sro.domain.lookup.address import Address, address_for
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.shared.hosts import system_of
from sro.domain.shared.identifiers import DeviceId

logger = logging.getLogger(__name__)

NO_TAB = frozenset({"no_tab_for_origin", "no_tab_for_system"})

K_DEADLINE_S = 45.0

K_WHILE_TALKING = 10.0


@dataclass(frozen=True, slots=True)
class Looked:
    lookup: Lookup
    ok: bool
    url: str = ""
    answer: Mapping[str, object] = field(default_factory=dict)
    read: Answer | None = None

    detail: str = ""


@dataclass(frozen=True, slots=True)
class Answers:
    plan: Plan
    looked: tuple[Looked, ...] = ()

    @property
    def any_answered(self) -> bool:
        return any(one.ok for one in self.looked)


class RunLookups:
    def __init__(self, uow: UnitOfWork, channel: Channel) -> None:
        self._uow = uow
        self._channel = channel

    async def execute(
        self,
        ctx: RequestContext,
        *,
        plan: Plan,
        device_id: DeviceId | None = None,
        allow_focus: bool = False,
        within: float = K_DEADLINE_S,
    ) -> Answers:
        if not plan.lookups:
            return Answers(plan=plan)

        device = device_id or next(iter(self._channel.online(ctx.tenant_id)), None)
        if device is None:
            return Answers(
                plan=plan,
                looked=tuple(
                    Looked(lookup=one, ok=False, detail="no browser is connected")
                    for one in plan.lookups
                ),
            )

        async with self._uow as uow:
            gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))

        looked = []
        for lookup in plan.lookups:
            address = address_for(lookup, gestures)
            if address is None:
                looked.append(
                    Looked(
                        lookup=lookup,
                        ok=False,
                        detail=f"nothing here has been to {lookup.target}",
                    )
                )
                continue
            looked.append(
                await self._one(
                    ctx, lookup, address, device, allow_focus=allow_focus, within=within
                )
            )
        return Answers(plan=plan, looked=tuple(looked))

    async def _one(
        self,
        ctx: RequestContext,
        lookup: Lookup,
        address: Address,
        device: DeviceId,
        *,
        allow_focus: bool,
        within: float = K_DEADLINE_S,
    ) -> Looked:
        if lookup.how == "call":
            reply = await self._send(ctx, device, "http.send", _call_payload(address), within)
            if _shut(reply):
                reply = await self._reopened(
                    ctx, device, address, "http.send", _call_payload(address), within
                )
            return _looked(lookup, address, reply)

        origin = system_of(address.url)
        going = {"url": address.url, "origin": origin, "allow_focus": allow_focus}
        moved = await self._send(ctx, device, "navigate", going, within)
        if _shut(moved):
            moved = await self._reopened(ctx, device, address, "navigate", going, within)
        if not moved.ok:
            return _looked(lookup, address, moved)
        shot = await self._send(
            ctx, device, "screenshot", {"origin": origin, "allow_focus": allow_focus}, within
        )
        return _looked(lookup, address, shot)

    async def _reopened(
        self,
        ctx: RequestContext,
        device: DeviceId,
        address: Address,
        kind: str,
        payload: Mapping[str, object],
        within: float = K_DEADLINE_S,
    ) -> Reply:
        opened = await self._send(ctx, device, "tab.open", {"url": address.url}, within)
        if not opened.ok:
            return opened
        return await self._send(ctx, device, kind, payload, within)

    async def _send(
        self,
        ctx: RequestContext,
        device: DeviceId,
        kind: str,
        payload: Mapping[str, object],
        within: float = K_DEADLINE_S,
    ) -> Reply:
        return await self._channel.send(
            ctx.tenant_id, device, kind=kind, payload=payload, deadline_s=within
        )


def _call_payload(address: Address) -> dict[str, object]:
    payload: dict[str, object] = {
        "method": "GET",
        "url": address.url,
        "headers": address.headers,
    }
    if address.live_headers:
        payload["live_headers"] = list(address.live_headers)
    return payload


def _looked(lookup: Lookup, address: Address, reply: Reply) -> Looked:
    result = reply.result if reply.ok else {}
    body = result.get("body") if isinstance(result, Mapping) else None
    return Looked(
        lookup=lookup,
        ok=reply.ok,
        url=address.url,
        answer=result,
        read=read_answer(body, url=address.url) if isinstance(body, str) else None,
        detail="" if reply.ok else reply.detail,
    )


def _shut(reply: Reply) -> bool:
    return not reply.ok and (reply.error_kind or "") in NO_TAB
