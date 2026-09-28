from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.execution.declared import declared_limits, names_of, screen_for
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.asking import (
    JOB,
    NEEDS,
    Pending,
    asking_state,
    opening,
    should_we,
    unusable,
)
from sro.domain.chat.thread import Said, Speaker
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.learned import offerable

logger = logging.getLogger(__name__)

DraftsForTheAsker = Callable[[RequestContext, Pending, str], Awaitable[bool]]


class AskAboutTheOffer:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        ids: IdFactory,
        drafts: DraftsForTheAsker | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._drafts: DraftsForTheAsker | None = drafts

    async def _only_required(self, ctx: RequestContext, pending: Pending) -> Pending:
        if not pending.workflow_id:
            return pending
        try:
            async with self._uow as uow:
                job = await uow.workflows.get(ctx.tenant_id, pending.workflow_id)
        except Exception:
            logger.exception("what else %s can set could not be read", pending.workflow_id)
            return pending
        optional = {name for name, _ in offerable(job.parameters, {})}
        bad = set(unusable(pending.values, pending.limits))
        values = {
            name: value
            for name, value in pending.values.items()
            if name not in optional or name not in bad
        }
        return replace(
            pending,
            values=values,
            missing=tuple(name for name in pending.missing if name not in optional),
            offered=offerable(job.parameters, values),
        )

    async def _what_the_boxes_hold(self, ctx: RequestContext, pending: Pending) -> dict[str, int]:
        known = dict(pending.limits)
        if not pending.workflow_id:
            return known
        try:
            async with self._uow as uow:
                job = await uow.workflows.get(ctx.tenant_id, pending.workflow_id)
            async with self._uow as uow:
                screen = await screen_for(uow, ctx.tenant_id, job)
                declared = await declared_limits(uow, ctx.tenant_id, names_of(job), screen)
        except Exception:
            logger.exception("the declared limits could not be read for %s", pending.workflow_id)
            return known
        for name, holds in declared.items():
            known[name] = min(holds, known[name]) if name in known else holds
        return known

    async def _should_we(
        self,
        ctx: RequestContext,
        pending: Pending,
        about: str,
        sent_to: Sequence[str],
        offer: str,
    ) -> str:
        asked = should_we(pending, about, sent_to)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(ctx.principal_id.value),
            text=asked,
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": JOB,
                "confirm": True,
                "workflow_id": pending.workflow_id,
                "title": pending.title,
                "values": dict(pending.values),
                "missing": [],
                "items": [dict(one) for one in pending.items],
                "mail_thread": pending.mail_thread,
                "sent_to": list(sent_to),
                "watched": pending.watched,
                **({"offer": offer} if offer else {}),
            },
        )
        logger.info(
            "%s: asking whether to run %s in the conversation", ctx.tenant_id.value, pending.title
        )
        return asked

    async def cannot_run(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        title: str,
        reasons: Sequence[str],
        about: str = "",
        mail_thread: str = "",
    ) -> str:
        said = (
            f"{title}{f' — {about}' if about.strip() else ''}. A request asks for this job, "
            f"but it cannot run yet: {'; '.join(reasons)}. Nothing was started."
        )
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(ctx.principal_id.value),
            text=said,
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": Said.NOTE,
                "workflow_id": workflow_id,
                "cannot_run": list(reasons),
                "mail_thread": mail_thread,
            },
        )
        logger.info("%s: a request asks for %s, which cannot run", ctx.tenant_id.value, workflow_id)
        return said

    async def execute(
        self,
        ctx: RequestContext,
        pending: Pending,
        *,
        about: str = "",
        mail_thread: str = "",
        ask_to_run: bool = False,
        sent_to: Sequence[str] = (),
        offer: str = "",
    ) -> str:
        pending = replace(pending, limits=await self._what_the_boxes_hold(ctx, pending))
        pending = await self._only_required(ctx, pending)
        pending = replace(
            pending,
            missing=tuple(
                dict.fromkeys((*pending.missing, *unusable(pending.values, pending.limits)))
            ),
        )
        if pending.ready:
            return await self._should_we(ctx, pending, about, sent_to, offer) if ask_to_run else ""
        asked = opening(pending, about)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(ctx.principal_id.value),
            text=asked,
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": NEEDS,
                "workflow_id": pending.workflow_id,
                "title": pending.title,
                "values": dict(pending.values),
                "missing": list(pending.missing),
                "offered": [list(one) for one in pending.offered],
                "items": [dict(one) for one in pending.items],
                "limits": dict(pending.limits),
                "mail_thread": pending.mail_thread,
                "from_step": pending.from_step,
                "watched": pending.watched,
                **({"unconfirmed": True} if ask_to_run else {}),
                **asking_state(pending),
            },
        )
        if self._drafts is not None and mail_thread.strip():
            try:
                await self._drafts(ctx, pending, mail_thread)
            except Exception:
                logger.exception("a mail to whoever asked could not be drafted")
        logger.info(
            "%s: asking about %s in the conversation -- %d value(s) still wanted",
            ctx.tenant_id.value,
            pending.title,
            len(pending.missing),
        )
        return asked


__all__ = ["AskAboutTheOffer"]
