"""Going and looking, one plan at a time.

`PlanLookups` says where the answer lives; this goes there. It is the half
that leaves the building, so everything it may do is narrow on purpose:

**A GET, or a page opened and photographed. Nothing else.** The plan cannot
express a write and `address_for` refuses anything that is not a recorded GET,
so a mail carrying "and then delete the old one" has no shape to become by the
time it reaches here.

**From the operator's own session.** The call goes out through the extension's
`http.send`, in the tab the operator is signed into, with the session cookie
the browser already has -- which is why this needs a connected browser and not
a credential in a file.

**A system nobody has open is opened, in the background.** Every command that
reaches a system needs a tab already on it -- the point of sending from the
browser is the session that origin's cookies carry -- so without `tab.open` a
question asked of four systems is answerable only for the ones the operator
happens to have in front of them. The tab is opened behind what they are
doing and their focus never moves.

**One lookup's failure is not the plan's.** A system with no tab open, an
endpoint this deployment has never been to, a page whose session token has
expired: each comes back as that lookup's own refusal beside the answers that
did arrive. A question asked of four systems and answered by three is three
answers and a named gap, which is worth more than nothing at all -- the
opposite reading from the PLANNER's, where a target nobody has seen refuses
the whole plan. The difference is that a planning failure means the plan is
wrong about the world, and a looking failure means one system was shut.
"""

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
"""The extension's two words for "nobody has that system open", which is the
one failure this side can do something about. Every other error kind -- a page
that would not answer, a header with no live source, a refused focus -- is a
fact about the attempt, and retrying it would just cost the same time twice."""

K_DEADLINE_S = 45.0
"""How long one lookup may take, when the lookup is what somebody is waiting on.

Longer than a run's step, which has an operator watching it: a lookup is
answered by whichever system is slowest, and a question that comes back
incomplete because a warehouse took twelve seconds is a worse outcome than one
that takes twelve seconds.

This is the budget for `/v1/lookups` and `/v1/ask`, where the answer IS the
request and nothing else is held up behind it."""

K_WHILE_TALKING = 10.0
"""And how long one may take when a CONVERSATION is waiting on it.

A reply in a panel is not a lookup somebody is watching a spinner for. It is a
turn in a conversation, and a turn that takes a minute has stopped being one.

Measured on the deployment 2026-09-21, request `req_10d3ff9b`:

    19:23:23  the sentence arrives
    19:23:38  device disconnected
    19:23:39  device connected
    19:24:19  device disconnected
    19:24:30  reply -- 67459ms

The browser's socket dropped twice inside one request. One command waited out
the full 45 seconds, the model calls either side cost the rest, and the person
who typed a question sat in front of a panel that said nothing for over a
minute. Before the conversation asked the lookup door at all, the same door
answered in 7691ms.

Ten seconds, because that is roughly twice what the whole of `/v1/ask` costs
end to end -- two model calls and a warehouse round trip measured at 5913ms on
the same deployment -- so a browser that is answering at all answers inside
it, and one that is not is not worth a conversation waiting on.

A lookup that runs out says so, and the thread stays usable. That is the
trade: a question answered late is worth less than a conversation that
kept going."""


@dataclass(frozen=True, slots=True)
class Looked:
    """What one lookup came back with."""

    lookup: Lookup
    ok: bool
    url: str = ""
    answer: Mapping[str, object] = field(default_factory=dict)
    read: Answer | None = None
    """The records in it, READ, rather than the body they arrived in.

    Every other read in this system goes through `read_answer`: the taught
    skill's own calls, a derived read, the capability probe. The lookup plane
    was the one that did not -- it handed the raw body on and left whoever
    drew it to parse JSON, pick columns and count rows.

    So each surface guessed, and the panel guessed badly. Measured on the
    deployment 2026-09-21: asked "is there a customer type called KKYT", it
    drew `URNFORMAT | ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` -- the first six
    KEYS of a payload that alphabetises -- as five columns of em dashes,
    beside a warehouse screen showing `Customer Type` and `Description`.

    `answer.py` had already solved every part of that, for the plane that uses
    it: a column earns its place by carrying a value, the ranking puts code,
    name and description first, `self_uri` is dropped as a link, two columns
    holding the same value in every row are one, the count is the system's own
    total rather than the page length, and `sentence()` says it in a line.

    None where there are no records to speak of -- a page of HTML, one scalar,
    a screen's photograph. Those keep `answer` and are drawn from it."""

    detail: str = ""
    """Why not, when not. Kept in the extension's own words -- `no_tab_for_origin`
    is a different problem from `unreachable`, and flattening them to "failed"
    throws away the one thing that says which."""


@dataclass(frozen=True, slots=True)
class Answers:
    plan: Plan
    looked: tuple[Looked, ...] = ()

    @property
    def any_answered(self) -> bool:
        return any(one.ok for one in self.looked)


class RunLookups:
    """Execute a plan against one browser."""

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
        """`within` is the caller's budget, because the callers have different
        ones: a lookup somebody asked for may take as long as the slowest
        warehouse, and a lookup inside a conversation turn may not. See
        `K_WHILE_TALKING`."""
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
            # Every gesture, scanned per lookup. The store holds hundreds per
            # tenant, so this is cheaper than the round trip that would fetch
            # one call.
            # ponytail: whole-store scan; a `calls_for_path` query if a tenant's
            # capture outgrows memory.
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

        # A screen takes two commands: put the page up, then photograph it.
        # Separate because the second one is the one that needs the operator's
        # permission to take their screen, and a navigate that worked is worth
        # saying so even when the picture is refused.
        # Scheme and host, which is what the extension matches a tab on --
        # `hosts.origin_of` answers the host alone, and that is the rule for
        # deciding whether two urls are one SYSTEM, not for finding a tab.
        origin = system_of(address.url)
        going = {"url": address.url, "origin": origin, "allow_focus": allow_focus}
        moved = await self._send(ctx, device, "navigate", going, within)
        if _shut(moved):
            # The tab `tab.open` makes is already ON the address, so the
            # navigate that follows is a no-op that confirms it -- cheaper than
            # a second code path, and it keeps the failure shape identical
            # whether the operator had the system open or not.
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
        """Open the system this command could not find, and ask it once more.

        Once. A second failure is a system that is open and still would not
        answer, which is a different problem and not one another tab fixes.
        """
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
        # `url` so the counting is honest: `limit=50` in the query and `50` in
        # the envelope are the same fact about what we ASKED for, and a total
        # that merely echoes our own paging is not a total.
        read=read_answer(body, url=address.url) if isinstance(body, str) else None,
        detail="" if reply.ok else reply.detail,
    )


def _shut(reply: Reply) -> bool:
    """Whether this failed because nobody has that system open."""
    return not reply.ok and (reply.error_kind or "") in NO_TAB
