from __future__ import annotations

import asyncio
from base64 import b64encode
from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from sro.application.context import RequestContext
from sro.application.execution.answer import Answer, read_answer
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.http import HttpCaller, HttpResponse, TargetUnreachable
from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.ports.pool import PoolFull
from sro.application.ports.repositories import UnitOfWork
from sro.application.runtime.api_lane import K_AUTH_REFUSED, needs_of, session_headers
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import Held
from sro.domain.lookup.address import Address, address_for
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.shared.errors import DomainError
from sro.domain.shared.hosts import REDACTED

K_GAPS = (DomainError, PoolFull, PageGone, TargetUnreachable, AccountBusy, BrowserUnavailable)


class MissingHeaders(DomainError):
    code = "missing_headers"


K_DEADLINE_S = 45.0

K_WHILE_TALKING = 10.0

K_AFTER_HEADERS_S = 1.0


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
    def __init__(self, uow: UnitOfWork, broker: SessionBroker, http: HttpCaller) -> None:
        self._uow, self._broker, self._http = uow, broker, http

    async def execute(
        self, ctx: RequestContext, *, plan: Plan, within: float = K_DEADLINE_S
    ) -> Answers:
        if not plan.lookups:
            return Answers(plan=plan)
        async with self._uow as uow:
            gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))
        looked: list[Looked] = []
        for lookup in plan.lookups:
            address = address_for(lookup, gestures)
            if address is None:
                looked.append(
                    Looked(
                        lookup=lookup, ok=False, detail=f"nothing here has been to {lookup.target}"
                    )
                )
                continue
            try:
                async with asyncio.timeout(within) as budget:
                    looked.append(await self._one(ctx, lookup, address, budget))
            except TimeoutError:
                looked.append(
                    Looked(
                        lookup=lookup,
                        ok=False,
                        url=address.url,
                        detail=f"timed out after {within:.0f} s",
                    )
                )
            except K_GAPS as gap:
                looked.append(Looked(lookup=lookup, ok=False, url=address.url, detail=str(gap)))
        return Answers(plan=plan, looked=tuple(looked))

    async def _one(
        self, ctx: RequestContext, lookup: Lookup, address: Address, budget: asyncio.Timeout
    ) -> Looked:
        page = address.page or address.url
        account = await self._broker.account_for(ctx, page)
        held = await self._broker.acquire(
            ctx, account, page, holder=f"lookup-{uuid4().hex}", park=False
        )
        try:
            if lookup.how == "call":
                got = await self._get(ctx, held, address, page, budget)
                if got.succeeded:
                    return _looked(lookup, address, {"status": got.status_code, "body": got.text})
            if await self._broker.signed_out(ctx, held):
                await self._broker.reauth(ctx, held, page, park=False)
            shot = await self._broker.screenshot(ctx, held)
            return _looked(
                lookup,
                address,
                {
                    "image_base64": b64encode(shot.image).decode(),
                    "mime_type": shot.mime_type,
                    "width": shot.width,
                    "height": shot.height,
                },
            )
        finally:
            await self._broker.release(ctx, held)

    async def _get(
        self, ctx: RequestContext, held: Held, address: Address, page: str, budget: asyncio.Timeout
    ) -> HttpResponse:
        got = await self._send(ctx, held, address, budget, fresh=False)
        if got.status_code in K_AUTH_REFUSED:
            await self._broker.reauth(ctx, held, page, park=False)
            got = await self._send(ctx, held, address, budget, fresh=True)
        return got

    async def _send(
        self,
        ctx: RequestContext,
        held: Held,
        address: Address,
        budget: asyncio.Timeout,
        *,
        fresh: bool,
    ) -> HttpResponse:
        needs = needs_of(dict.fromkeys((*address.live_headers, *address.struck), REDACTED))
        left = (budget.when() or 0.0) - asyncio.get_running_loop().time() - K_AFTER_HEADERS_S
        headers = await session_headers(
            self._broker,
            ctx,
            held,
            address.url,
            address.headers,
            fresh=fresh,
            needs=needs,
            wait_s=max(0.0, left),
        )
        carried = {name.lower() for name in headers}
        missing = [name for name in needs if name not in carried]
        if missing:
            raise MissingHeaders(f"the session has no {', '.join(missing)} for this read")
        return await self._http.send("GET", address.url, headers=headers)


def _looked(lookup: Lookup, address: Address, result: Mapping[str, object]) -> Looked:
    body = result.get("body")
    return Looked(
        lookup=lookup,
        ok=True,
        url=address.url,
        answer=result,
        read=read_answer(body, url=address.url) if isinstance(body, str) else None,
    )
