from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.execution.declared import declared_limits, names_of, screen_for
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.asking import JOB, NEEDS, Pending, opening, should_we, unusable
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

    async def _also_settable(
        self, ctx: RequestContext, pending: Pending
    ) -> tuple[tuple[str, str], ...]:
        if not pending.workflow_id:
            return ()
        try:
            async with self._uow as uow:
                job = await uow.workflows.get(ctx.tenant_id, pending.workflow_id)
        except Exception:
            logger.exception("what else %s can set could not be read", pending.workflow_id)
            return ()
        return offerable(job.parameters, pending.values) if job else ()

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
        self, ctx: RequestContext, pending: Pending, about: str, sent_to: Sequence[str]
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
            },
        )
        logger.info(
            "%s: asking whether to run %s in the conversation", ctx.tenant_id.value, pending.title
        )
        return asked

    async def execute(
        self,
        ctx: RequestContext,
        pending: Pending,
        *,
        about: str = "",
        mail_thread: str = "",
        ask_to_run: bool = False,
        sent_to: Sequence[str] = (),
    ) -> str:
        pending = replace(pending, limits=await self._what_the_boxes_hold(ctx, pending))
        pending = replace(
            pending,
            missing=tuple(
                dict.fromkeys((*pending.missing, *unusable(pending.values, pending.limits)))
            ),
            offered=await self._also_settable(ctx, pending),
        )
        if pending.ready:
            return await self._should_we(ctx, pending, about, sent_to) if ask_to_run else ""
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


class SayTheRunStarted:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, *, run_id: str, title: str) -> None:
        if not run_id.strip():
            return
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(ctx.principal_id.value),
            text=f"Running {title}…" if title.strip() else "Running it…",
            speaker=Speaker.SYSTEM,
            decision={"kind": Said.RUN, "run_id": run_id, "title": title},
        )
        logger.info("%s: %s is running as %s", ctx.tenant_id.value, title or "a job", run_id)


__all__ = ["AskAboutTheOffer", "SayTheRunStarted"]
