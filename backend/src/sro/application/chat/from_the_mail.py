from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.mailbox import K_REMEMBER, SERVER, sent_to_others
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.understand import understand
from sro.application.context import RequestContext
from sro.application.execution.declared import (
    declared_keys,
    declared_limits,
    names_of,
    screen_for,
)
from sro.application.execution.gather import GatherContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.spend import over_cap
from sro.application.observation.record_attempt import RecordAttempt
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.application.runtime.answer_run import K_ANSWER, AnswerRun
from sro.application.shared.refusals import OverCap
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.asking import NEEDS, Pending, pending_job, question
from sro.domain.chat.thread import Speaker
from sro.domain.execution.learned_step import limits_for, too_long
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import read_wait, still_waiting
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.attempts import DONE
from sro.domain.shared.errors import Conflict
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import offerable
from sro.domain.skill.workflow import Workflow

K_LOOK = 8

K_LOOK_PAGES = 10

K_THREAD = 8000

K_OFFER_ROUNDS = 3

K_SUBJECT = 120

K_BECAUSE = 400

K_RECENT = "newer_than:2d -in:chats"

K_TEXT = 2000


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Offered:
    message: str
    workflow_id: str
    title: str
    values: Mapping[str, str] = field(default_factory=dict)
    missing: Sequence[str] = ()

    offers: Sequence[tuple[str, str]] = ()

    unasked: Sequence[str] = ()

    aside: Mapping[str, str] = field(default_factory=dict)

    placed: Mapping[str, str] = field(default_factory=dict)

    started: bool = False

    subject: str = ""

    thread: str = ""

    too_long: Mapping[str, int] = field(default_factory=dict)

    sure: bool = False

    sent_to: Sequence[str] = ()


@dataclass(frozen=True, slots=True)
class LookedInTheMail:
    offered: tuple[Offered, ...] = ()
    read: int = 0
    why: str = ""
    spent: Answer = field(default_factory=Answer)


class FromTheMail:
    def __init__(
        self,
        uow: UnitOfWork,
        tools: ToolCaller,
        asker: Asker | None,
        *,
        model: str,
        answer: AnswerRun,
        gather: GatherContext | None = None,
        clock: Clock | None = None,
        ids: IdFactory | None = None,
        cap_usd: float = -1.0,
        start: StartWorkflowRun | None = None,
        attempts: RecordAttempt | None = None,
    ) -> None:
        self._uow = uow
        self._start = start
        self._attempts = attempts
        self._tools = tools
        self._asker = asker
        self._model = model
        self._answer = answer
        self._gather = gather
        self._clock = clock
        self._ids = ids
        self._cap_usd = cap_usd

    async def execute(self, ctx: RequestContext, *, limit: int = K_LOOK) -> LookedInTheMail:
        asker = asker_or_refuse(self._asker)
        now = datetime.now(tz=UTC)
        async with self._uow as uow:
            why = await over_cap(
                uow,
                ctx.tenant_id,
                now=self._clock.now() if self._clock is not None else now,
                cap_usd=self._cap_usd,
            )
            if why is not None:
                raise OverCap(why)
            workflows = list(await uow.workflows.known(ctx.tenant_id))
            if not workflows:
                return LookedInTheMail(why="this tenant has no mined jobs to recognise")
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id,
                ids=tuple(
                    sorted({one for w in workflows for step in w.steps for one in step.cites})
                ),
            )
        by_id = {gesture.id: gesture for gesture in cited}
        asked_by = {w.id: mails for w in workflows if (mails := texts(mails_behind(w, by_id)))}
        titles = {w.id: w.title for w in workflows}
        held = {w.id: w for w in workflows}

        try:
            arrivals, more = await self._recent(ctx, limit)
        except ToolsUnavailable as gone:
            return LookedInTheMail(why=f"the mailbox could not be reached: {gone}")

        offered: list[Offered] = []
        spent = Answer()
        read = 0
        unsure = 0
        tenant = ctx.tenant_id.value
        async for message in self._unclaimed(ctx, arrivals, more, limit, now=now):
            try:
                try:
                    said, thread, subject, sent_to = await self._body(ctx, message)
                except ToolsUnavailable as gone:
                    return LookedInTheMail(
                        offered=tuple(offered), read=read, why=str(gone), spent=spent
                    )
                if not said:
                    continue
                read += 1
                back = await self._answering(ctx, thread)
                if back is not None and back.executor == "steel":
                    await self._answer_the_run(ctx, back, said)
                    continue
                if back is not None:
                    offered.append(
                        await self._carrying_on(
                            ctx, message, back, said, thread, subject, titles, held
                        )
                    )
                    continue
                asked = await self._was_asked(ctx, thread)
                if asked is not None:
                    offered.append(
                        await self._answered_by_mail(
                            ctx, message, asked, said, thread, subject, held
                        )
                    )
                    continue
                got = await understand(said, workflows, asker, self._model, asked_by)
                spent = _also(spent, got.answer)
                if got.workflow_id is None:
                    logger.info("%s: read a mail that asks for no job this tenant holds", tenant)
                    continue
                if not got.sure:
                    unsure += 1
                    logger.info(
                        "%s: read a mail asking for %s but could not tell it from %s",
                        tenant,
                        titles.get(got.workflow_id, got.workflow_id),
                        ", ".join(titles.get(one, one) for one in got.also) or "another job",
                    )
                    continue
                values, missing = dict(got.values), list(got.missing)
                asked_for_too: set[str] = set()
                said_besides: dict[str, str] = {}
                if missing:
                    job_ = titles.get(got.workflow_id, got.workflow_id)
                    if not thread:
                        logger.info("%s: %s -- the mail names no conversation", tenant, job_)
                    else:
                        whole = await self._conversation(ctx, thread)
                        if not whole:
                            logger.info("%s: %s -- the conversation read back empty", tenant, job_)
                        elif whole == said:
                            logger.info(
                                "%s: %s -- the conversation is only this mail", tenant, job_
                            )
                        else:
                            again = await understand(whole, workflows, asker, self._model, asked_by)
                            spent = _also(spent, again.answer)
                            if again.workflow_id != got.workflow_id:
                                logger.info(
                                    "%s: %s -- the conversation read as %s instead",
                                    tenant,
                                    job_,
                                    titles.get(again.workflow_id or "", again.workflow_id)
                                    or "no job at all",
                                )
                            else:
                                values |= dict(again.values)
                                asked_for_too.update(again.unasked)
                                said_besides.update(again.aside)
                                missing = [name for name in missing if name not in values]
                                logger.info(
                                    "%s: %s -- the conversation gave %d of %d",
                                    tenant,
                                    job_,
                                    len(values),
                                    len(values) + len(missing),
                                )
                if missing and self._gather is not None:
                    found = await self._gather.execute(
                        ctx,
                        job=titles.get(got.workflow_id, got.workflow_id),
                        wanted=missing,
                        because=said[:K_BECAUSE],
                        rounds=K_OFFER_ROUNDS,
                    )
                    values |= {name: one.value for name, one in found.values.items()}
                    missing = [name for name in missing if name not in values]
                    logger.info(
                        "%s: gathered %d of %d for %s (%s)",
                        tenant,
                        len(found.values),
                        len(found.values) + len(missing),
                        titles.get(got.workflow_id, got.workflow_id),
                        found.why or "no reason given",
                    )
                offered.append(
                    Offered(
                        message=message,
                        workflow_id=got.workflow_id,
                        title=titles.get(got.workflow_id, got.workflow_id),
                        values=values,
                        missing=missing,
                        thread=thread,
                        subject=subject,
                        offers=offerable(
                            next(
                                (w.parameters for w in workflows if w.id == got.workflow_id),
                                (),
                            ),
                            values,
                        ),
                        unasked=sorted({*got.unasked, *asked_for_too}),
                        aside={**got.aside, **said_besides},
                        sure=True,
                        sent_to=sent_to,
                    )
                )
            except OverCap as reached:
                await self._forget(ctx, message)
                logger.info("%s: the look stopped at the cap -- %s", tenant, reached)
                return LookedInTheMail(
                    offered=await self._start_each(
                        ctx, await self._what_will_not_fit(ctx, offered, workflows)
                    ),
                    read=read,
                    why=str(reached),
                    spent=spent,
                )
        looked = LookedInTheMail(
            offered=await self._start_each(
                ctx, await self._what_will_not_fit(ctx, offered, workflows)
            ),
            read=read,
            why=_sentence(offered, read, unsure),
            spent=spent,
        )
        logger.info(
            "%s: looked in the mail -- %d read, %d offered (%s)",
            tenant,
            read,
            len(offered),
            looked.why,
        )
        return looked

    async def _start_each(
        self, ctx: RequestContext, offered: Sequence[Offered]
    ) -> tuple[Offered, ...]:
        started: list[Offered] = []
        for one in offered:
            try:
                started.append(await self._started(ctx, one))
            except OverCap as reached:
                await self._forget(ctx, one.message)
                logger.info(
                    "%s: %s left unread, its run refused at the cap -- %s",
                    ctx.tenant_id.value,
                    one.message,
                    reached,
                )
        return tuple(started)

    async def _started(self, ctx: RequestContext, one: Offered) -> Offered:
        if (
            not one.sure
            or one.missing
            or one.too_long
            or one.started
            or one.sent_to
            or self._start is None
            or not self._start.runs_on_steel(ctx)
        ):
            return one
        async with self._uow as uow:
            if await uow.workflow_runs.started_on(ctx.tenant_id, server=SERVER, thread=one.thread):
                logger.info(
                    "%s: %s already started a run, so this mail is only offered",
                    ctx.tenant_id.value,
                    one.thread,
                )
                return one
        try:
            run = await self._start.execute(
                ctx,
                workflow_id=one.workflow_id,
                device_id=None,
                values=dict(one.values),
                live=True,
                allow_focus=False,
                conversation=(SERVER, one.thread),
            )
        except OverCap:
            raise
        except Exception:
            logger.exception(
                "%s: a sure, complete mail could not start its run", ctx.tenant_id.value
            )
            return one
        if not await self._start.start_on_steel(ctx, run):
            return one
        if self._attempts is not None:
            await self._attempts.execute(
                ctx,
                asked_for="start a job from a mail",
                came_of=DONE,
                about={"run": run.id, "workflow": one.workflow_id, "thread": one.thread},
            )
        return replace(one, started=True)

    async def _answering(self, ctx: RequestContext, thread: str) -> WorkflowRun | None:
        if not thread.strip():
            return None
        async with self._uow as uow:
            waiting = await uow.workflow_runs.waiting_on(
                ctx.tenant_id, server=SERVER, thread=thread
            )
        if waiting is None or not still_waiting(read_wait(waiting.awaiting), datetime.now(tz=UTC)):
            return None
        return waiting

    async def _answer_the_run(self, ctx: RequestContext, run: WorkflowRun, said: str) -> None:
        asking = Progress.of(run.progress).asking
        if run.outcome != "running" or asking.get("kind") != "value":
            logger.info(
                "%s: a reply on %s's thread answers nothing: only a value is taken from mail, "
                "and whatever %s asks stands in the panel",
                ctx.tenant_id.value,
                run.id,
                run.id,
            )
            return
        try:
            await self._answer.execute(
                ctx, run_id=run.id, question_id=asking["id"], value=said[:K_ANSWER]
            )
        except Conflict as refused:
            logger.info(
                "%s: a reply on %s's thread was not taken as its answer: %s",
                ctx.tenant_id.value,
                run.id,
                refused,
            )

    async def _was_asked(self, ctx: RequestContext, thread: str) -> Pending | None:
        if not thread.strip():
            return None
        found = await ReadThreads(self._uow).current(ctx)
        if found is None:
            return None
        async with self._uow as uow:
            conversation = await uow.threads.get(ctx.tenant_id, found.id)
        waiting = pending_job(conversation.messages)
        return waiting if waiting is not None and waiting.mail_thread == thread else None

    async def _carrying_on(
        self,
        ctx: RequestContext,
        message: str,
        back: WorkflowRun,
        said: str,
        thread: str,
        subject: str,
        titles: Mapping[str, str],
        held: Mapping[str, Workflow] = MappingProxyType({}),
    ) -> Offered:
        values = dict(back.values)
        missing = [name for name in back.needs if name not in values]
        values |= await self._reply_says(ctx, said, held.get(back.workflow_id), missing)
        missing = [name for name in missing if name not in values]
        if missing and self._gather is not None:
            found = await self._gather.execute(
                ctx,
                job=titles.get(back.workflow_id, back.workflow_id),
                wanted=missing,
                because=said[:K_BECAUSE],
                rounds=K_OFFER_ROUNDS,
            )
            values |= {name: one.value for name, one in found.values.items()}
            missing = [name for name in missing if name not in values]
        logger.info(
            "%s: a reply carries on %s (%d of %d answered)",
            ctx.tenant_id.value,
            back.id,
            len(back.needs) - len(missing),
            len(back.needs),
        )
        return Offered(
            message=message,
            workflow_id=back.workflow_id,
            title=titles.get(back.workflow_id, back.workflow_id),
            values=values,
            missing=missing,
            thread=thread,
            subject=subject,
        )

    async def _answered_by_mail(
        self,
        ctx: RequestContext,
        message: str,
        asked: Pending,
        said: str,
        thread: str,
        subject: str,
        held: Mapping[str, Workflow] = MappingProxyType({}),
    ) -> Offered:
        values = dict(asked.values)
        missing = [name for name in asked.missing if name not in values or not values[name]]
        values |= await self._reply_says(ctx, said, held.get(asked.workflow_id), missing)
        missing = [name for name in missing if name not in values]
        if missing and self._gather is not None:
            found = await self._gather.execute(
                ctx,
                job=asked.title,
                wanted=missing,
                because=said[:K_BECAUSE],
                rounds=K_OFFER_ROUNDS,
            )
            values |= {name: one.value for name, one in found.values.items()}
            missing = [name for name in missing if name not in values]
        logger.info(
            "%s: a reply answers the question standing on %s (%d of %d)",
            ctx.tenant_id.value,
            thread,
            len(asked.missing) - len(missing),
            len(asked.missing),
        )
        started = await self._the_question_is_answered(ctx, asked, values, missing, said_by=subject)
        return Offered(
            started=started,
            message=message,
            workflow_id=asked.workflow_id,
            title=asked.title,
            values=values,
            missing=missing,
            thread=thread,
            subject=subject,
        )

    async def _reply_says(
        self,
        ctx: RequestContext,
        said: str,
        job: Workflow | None,
        wanted: Sequence[str],
    ) -> dict[str, str]:
        if not wanted or job is None or self._asker is None or not said.strip():
            return {}
        read = await understand(said, [job], self._asker, self._model)
        got = {
            name: value
            for name, value in read.values.items()
            if name in set(wanted) and str(value).strip()
        }
        if got:
            logger.info(
                "%s: the reply itself answers %s",
                ctx.tenant_id.value,
                ", ".join(sorted(got)),
            )
        return got

    async def _the_question_is_answered(
        self,
        ctx: RequestContext,
        asked: Pending,
        values: Mapping[str, str],
        missing: Sequence[str],
        *,
        said_by: str = "",
    ) -> bool:
        if self._clock is None or self._ids is None:
            return False
        try:
            found = await ReadThreads(self._uow).current(ctx)
            if found is None:
                return False
            filled = {name: values[name] for name in asked.missing if values.get(name)}
            named = ", ".join(f"{name} {value}" for name, value in filled.items())
            about = f" to {said_by}" if said_by.strip() else ""
            still = Pending(
                workflow_id=asked.workflow_id,
                title=asked.title,
                values=dict(values),
                missing=tuple(missing),
                items=asked.items,
                watched=asked.watched,
                limits=asked.limits,
                from_step=asked.from_step,
                mail_thread=asked.mail_thread,
            )
            said = f"A reply{about} answered: {named or 'nothing I could use'}." + (
                f" {question(still)}" if missing else f" Running {still.title} now."
            )
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=ctx.principal_id,
                text=said,
                speaker=Speaker.ASSISTANT,
                decision=(
                    {
                        "kind": NEEDS,
                        "workflow_id": still.workflow_id,
                        "title": still.title,
                        "values": dict(still.values),
                        "items": [dict(one) for one in still.items],
                        "missing": list(still.missing),
                        "watched": still.watched,
                        "limits": dict(still.limits),
                        "from_step": still.from_step,
                        "mail_thread": still.mail_thread,
                    }
                    if missing
                    else {
                        "kind": "job",
                        "workflow_id": still.workflow_id,
                        "title": still.title,
                        "values": dict(still.values),
                        "items": [dict(one) for one in still.items],
                        "missing": [],
                        "limits": dict(still.limits),
                        "from_step": still.from_step,
                        "mail_thread": still.mail_thread,
                        "watched": still.watched,
                        "resume": True,
                    }
                ),
            )
        except Exception:
            logger.exception("the answered question could not be closed")
            return False
        return not missing

    async def _what_will_not_fit(
        self, ctx: RequestContext, offered: Sequence[Offered], jobs: Sequence[Workflow]
    ) -> tuple[Offered, ...]:
        by_id = {one.id: one for one in jobs}
        limits: dict[str, dict[str, int]] = {}
        placeable: dict[str, dict[str, str]] = {}
        for workflow_id in sorted({one.workflow_id for one in offered}):
            job = by_id.get(workflow_id)
            if job is None:
                continue
            async with self._uow as uow:
                learnt = await uow.workflows.learned_for(workflow_id)
            found = limits_for(
                job.steps,
                learnt,
                await declared_limits(
                    self._uow,
                    ctx.tenant_id,
                    names_of(job),
                    await screen_for(self._uow, ctx.tenant_id, job),
                ),
            )
            if found:
                limits[workflow_id] = found
            asked = sorted(
                {name for one in offered if one.workflow_id == workflow_id for name in one.unasked}
            )
            if asked:
                placeable[workflow_id] = await declared_keys(
                    self._uow,
                    ctx.tenant_id,
                    asked,
                    await screen_for(self._uow, ctx.tenant_id, job),
                )
        return tuple(_told(one, limits, placeable) for one in offered)

    async def _unclaimed(
        self,
        ctx: RequestContext,
        arrivals: list[str],
        more: str,
        limit: int,
        *,
        now: datetime,
    ) -> AsyncIterator[str]:
        pages = 1
        while True:
            fresh = False
            for message in arrivals:
                if await self._first_time(ctx, message, now=now):
                    fresh = True
                    yield message
            if not fresh or not more:
                return
            if pages == K_LOOK_PAGES:
                logger.warning(
                    "%s: %d pages of new mail in one look; older mail in the window is not read",
                    ctx.tenant_id.value,
                    K_LOOK_PAGES,
                )
                return
            try:
                arrivals, more = await self._recent(ctx, limit, page=more)
            except ToolsUnavailable as gone:
                logger.info(
                    "%s: the next page of mail could not be read -- %s", ctx.tenant_id.value, gone
                )
                return
            pages += 1

    async def _recent(
        self, ctx: RequestContext, limit: int, *, page: str = ""
    ) -> tuple[list[str], str]:
        answered = await self._tools.call(
            ctx.tenant_id,
            ctx.principal_id,
            SERVER,
            "search_threads",
            {"query": K_RECENT, "limit": str(limit), **({"page": page} if page else {})},
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return [], ""
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list):
            return [], ""
        more = said.get("next_page")
        return [
            str(row["id"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        ][:limit], more if isinstance(more, str) else ""

    async def _body(
        self, ctx: RequestContext, message: str
    ) -> tuple[str, str, str, tuple[str, ...]]:
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return "", "", "", ()
        if not isinstance(said, dict):
            return "", "", "", ()
        whole = " ".join(
            str(said.get(part) or "").strip() for part in ("subject", "body", "snippet")
        )
        whole = " ".join(whole.split())
        return (
            whole[:K_TEXT],
            str(said.get("thread_id") or ""),
            " ".join(str(said.get("subject") or "").split())[:K_SUBJECT],
            sent_to_others(
                *(str(said.get(part) or "") for part in ("from", "to", "cc", "mailbox"))
            ),
        )

    async def _conversation(self, ctx: RequestContext, thread: str) -> str:
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_thread", {"id": thread}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return ""
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list):
            return ""
        whole = " ".join(
            " ".join(str(one.get(part) or "") for part in ("subject", "body"))
            for one in rows
            if isinstance(one, dict)
        )
        return " ".join(whole.split())[:K_THREAD]

    async def _forget(self, ctx: RequestContext, message: str) -> None:
        async with self._uow as uow:
            await uow.tool_calls.forget(ctx.tenant_id, _mail_key(message))
            await uow.commit()

    async def _first_time(self, ctx: RequestContext, message: str, *, now: datetime) -> bool:
        async with self._uow as uow:
            first = await uow.tool_calls.remember(
                ctx.tenant_id,
                _mail_key(message),
                tool="read a mail for what it asks",
                at=now,
                stale_after=K_REMEMBER,
            )
            await uow.commit()
        return first


def _mail_key(message: str) -> str:
    return f"mail:{message}"


def _sentence(offered: Sequence[Offered], read: int, unsure: int = 0) -> str:
    if not read:
        return "no mail has arrived since the last look"
    if not offered and unsure:
        return f"read {read}, and {unsure} asked for a job this tenant holds more than one of"
    if not offered:
        return f"read {read}, and none of them asks for a job this tenant holds"
    return "offered " + ", ".join(one.title for one in offered)


def _also(running: Answer, answer: Answer) -> Answer:
    return Answer(
        in_tokens=running.in_tokens + answer.in_tokens,
        out_tokens=running.out_tokens + answer.out_tokens,
        thought_tokens=running.thought_tokens + answer.thought_tokens,
        cost_usd=running.cost_usd + answer.cost_usd,
        unpriced=running.unpriced or answer.unpriced,
    )


__all__ = ["FromTheMail", "LookedInTheMail", "Offered"]


def _told(
    one: Offered,
    limits: Mapping[str, Mapping[str, int]],
    placeable: Mapping[str, Mapping[str, str]],
) -> Offered:
    holds = limits.get(one.workflow_id) or {}
    keys = placeable.get(one.workflow_id) or {}
    told = replace(one, too_long=too_long(one.values, holds)) if holds else one
    if not keys:
        return told
    return replace(
        told,
        unasked=[name for name in told.unasked if name not in keys],
        values={**told.values, **{name: told.aside[name] for name in keys if name in told.aside}},
        placed=dict(keys),
    )
