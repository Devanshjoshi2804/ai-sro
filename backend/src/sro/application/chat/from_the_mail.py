from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from types import MappingProxyType

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.candidates import candidate_of
from sro.application.chat.mailbox import (
    K_ELSEWHERE,
    K_REMEMBER,
    K_TAKEN,
    SERVER,
    elsewhere_key,
    is_ours,
    mail_key,
    sent_to_others,
)
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.understand import held_runs, offer_check, read_request, understand
from sro.application.connection.sign_in import logins_of
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
from sro.application.skill.job_facts import JobFacts, job_facts
from sro.domain.chat.asking import (
    FROM_THE_MAIL,
    FROM_THE_REPLY,
    NEEDS,
    Pending,
    asked_by_mail,
    changes,
    question,
    quoted,
    sourced,
    waiting_on_mail,
)
from sro.domain.chat.thread import Said, Speaker
from sro.domain.execution.learned_step import limits_for, too_long
from sro.domain.execution.mail_job import MAIL_BODY, addresses_in, one_address_in, sender_address
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import read_wait, still_waiting
from sro.domain.execution.workflow_run import WorkflowRun, answers_for
from sro.domain.observation.attempts import DONE
from sro.domain.prompts.record import quoted_in
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.shared.errors import Conflict
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import offerable
from sro.domain.skill.signing_in import Logins
from sro.domain.skill.workflow import Workflow

K_LOOK = 8

K_LOOK_PAGES = 10

K_LEASE = timedelta(minutes=15)

K_READ_TOOL = "read a mail for what it asks"

K_PAGE_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,256}")

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

    asked: bool = False

    cannot_run: Sequence[str] = ()

    fresh: bool = True

    sender: str = ""

    arrived: str = ""

    offer: str = ""

    answered: Sequence[str] = ()

    @property
    def named(self) -> str:
        return self.offer or mail_key(self.message)


@dataclass(frozen=True, slots=True)
class LookedInTheMail:
    offered: tuple[Offered, ...] = ()
    read: int = 0
    why: str = ""
    spent: Answer = field(default_factory=Answer)
    asks_nothing: tuple[str, ...] = ()
    busy: int = 0
    stopped: str = ""

    def said(self) -> str:
        lines = [f"{_about(one.subject)} — {_came_to(one)}." for one in self.offered]
        lines += [f"a mail that asks for no job here: {_about(one)}." for one in self.asks_nothing]
        if self.busy:
            lines.append(
                f"{self.busy} mail{' is' if self.busy == 1 else 's are'} being read by another "
                "look right now; what it asks will show here when that look is done."
            )
        if self.stopped:
            lines.append(f"the look stopped there: {self.stopped}.")
        if not lines:
            return f"Looked in the mail: {self.why}."
        return "Looked in the mail:\n" + "\n".join(f"- {one}" for one in lines)


class FromTheMail:
    def __init__(
        self,
        uow: UnitOfWork,
        tools: ToolCaller,
        asker: Asker | None,
        *,
        answer: AnswerRun,
        gather: GatherContext | None = None,
        clock: Clock | None = None,
        ids: IdFactory | None = None,
        cap_usd: float = -1.0,
        start: StartWorkflowRun | None = None,
        attempts: RecordAttempt | None = None,
        asks: AskAboutTheOffer | None = None,
    ) -> None:
        self._uow = uow
        self._asks = asks
        self._start = start
        self._attempts = attempts
        self._tools = tools
        self._asker = asker
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
            facts = await job_facts(uow, ctx.tenant_id, workflows, now=now)
            held_by = await held_runs(uow, ctx.tenant_id)
            logins = await logins_of(uow, ctx.tenant_id)
        titles = {w.id: w.title for w in workflows}
        held = {one.workflow.id: one for one in facts}

        try:
            arrivals, more = await self._recent(ctx, limit)
        except ToolsUnavailable as gone:
            return LookedInTheMail(why=f"the mailbox could not be reached: {gone}")

        offered: list[Offered] = []
        look = _Look()
        reach = _Reach()
        known = _Known(workflows, asker, facts, titles, held, held_by, now, logins)
        tenant = ctx.tenant_id.value
        async for message in self._unclaimed(ctx, arrivals, more, limit, now=now, reach=reach):
            try:
                one = await self._read(ctx, message, look, known)
                if one is not None:
                    one = await self._settle(ctx, one, workflows)
            except _Theirs:
                await self._release(ctx, message)
                continue
            except (OverCap, ToolsUnavailable, Unread) as stopped:
                await self._release(ctx, message)
                logger.info("%s: the look stopped at %s -- %s", tenant, message, stopped)
                return LookedInTheMail(
                    offered=tuple(offered),
                    read=look.read,
                    why=str(stopped),
                    spent=look.spent,
                    asks_nothing=tuple(look.asks_nothing),
                    busy=reach.busy,
                    stopped=str(stopped),
                )
            except BaseException:
                await self._release(ctx, message)
                raise
            await self._keep(ctx, message, now=now)
            if one is not None:
                offered.append(one)
        if reach.whole and arrivals:
            await self._caught_up(ctx, arrivals[0], now=now)
        looked = LookedInTheMail(
            offered=tuple(offered),
            read=look.read,
            why=_sentence(offered, look.read, look.unsure, look.theirs),
            spent=look.spent,
            asks_nothing=tuple(look.asks_nothing),
            busy=reach.busy,
        )
        logger.info(
            "%s: looked in the mail -- %d read, %d offered (%s)",
            tenant,
            look.read,
            len(offered),
            looked.why,
        )
        return looked

    async def _read(
        self, ctx: RequestContext, message: str, look: _Look, known: _Known
    ) -> Offered | None:
        workflows, asker, titles, held = known.workflows, known.asker, known.titles, known.held
        tenant = ctx.tenant_id.value
        mail = await self._body(ctx, message)
        said, thread, subject, sent_to, marker = (
            mail.said,
            mail.thread,
            mail.subject,
            mail.sent_to,
            mail.marker,
        )
        if not said:
            return None
        if await is_ours(
            self._uow,
            ctx,
            {"id": message, "marker": marker},
            since=datetime.now(tz=UTC) - K_REMEMBER,
        ):
            return None
        look.read += 1
        back = await self._answering(ctx, thread)
        waits = Progress.of(back.progress).asking.get("kind") if back is not None else None
        if back is not None and (back.executor == "steel" or waits in ("recipient", MAIL_BODY)):
            if not answers_for(back, ctx.principal_id.value):
                look.theirs += 1
                await self._elsewhere(ctx, back)
                raise _Theirs
            await self._answer_the_run(ctx, back, said, message)
            return None
        if back is not None:
            return await self._carrying_on(ctx, message, back, said, thread, subject, titles, held)
        asked, asked_of = await self._was_asked(ctx, thread)
        if asked is not None and (not asked_of or asked_of == sender_address(mail.sender)):
            return await self._answered_by_mail(ctx, message, asked, said, thread, subject, held)
        whole, earlier = await self._conversation(ctx, thread, message) if thread else ("", "")
        text = whole or said
        got = await read_request(text, known.facts, asker, held=known.held_by, logins=known.logins)
        look.spent = _also(look.spent, got.answer)
        if got.answer.data is None:
            raise Unread(got.answer.error or "the model gave no reading")
        async with self._uow as uow:
            got = await offer_check(uow, ctx.tenant_id, got, known.facts, now=known.now)
        if got.workflow_id is None:
            logger.info("%s: read a mail that asks for no job this tenant holds", tenant)
            look.asks_nothing.append(subject)
            return None
        if not got.sure:
            look.unsure += 1
            logger.info(
                "%s: read a mail asking for %s but could not tell it from %s",
                tenant,
                titles.get(got.workflow_id, got.workflow_id),
                ", ".join(titles.get(one, one) for one in got.also) or "another job",
            )
        values, missing = dict(got.values), list(got.missing)
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
                "%s: gathered for %s -- found %s; still missing %s (%s)",
                tenant,
                titles.get(got.workflow_id, got.workflow_id),
                ", ".join(found.values) or "nothing",
                ", ".join(missing) or "nothing",
                found.why or "no reason given",
            )
        return Offered(
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
            unasked=got.unasked,
            aside=got.aside,
            sure=got.sure,
            sent_to=sent_to,
            cannot_run=got.cannot_run,
            sender=mail.sender,
            arrived=mail.arrived,
            fresh=not earlier
            or any(
                not quoted_in(value, earlier)
                for one in (got.values, *got.items)
                for value in one.values()
            ),
        )

    async def _settle(
        self, ctx: RequestContext, one: Offered, workflows: Sequence[Workflow]
    ) -> Offered:
        (one,) = await self._what_will_not_fit(ctx, [one], workflows)
        if one.too_long:
            logger.info(
                "%s: %s cannot take what the mail gave -- %s",
                ctx.tenant_id.value,
                one.title,
                "; ".join(
                    f"{name} is {len(one.values.get(name, ''))} characters, takes {holds}"
                    for name, holds in one.too_long.items()
                ),
            )
        if one.cannot_run and self._asks is not None:
            await self._asks.cannot_run(
                ctx,
                workflow_id=one.workflow_id,
                title=one.title,
                reasons=one.cannot_run,
                about=one.subject,
                mail_thread=one.thread,
            )
            return replace(one, asked=True)
        if not one.fresh and await self._started_here(ctx, one.thread):
            await self._about_the_run(ctx, one)
            return replace(one, asked=True)
        if one.fresh:
            one = await self._started(ctx, one)
        if (
            one.started
            or self._asks is None
            or self._start is None
            or not self._start.runs_on_steel(ctx)
        ):
            return one
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
            ask_to_run=True,
            sure=one.sure and not one.sent_to,
            sent_to=one.sent_to,
            offer=one.named,
            mail=_envelope(one),
        )
        return replace(one, asked=True)

    async def _started_here(self, ctx: RequestContext, thread: str) -> bool:
        async with self._uow as uow:
            return await uow.workflow_runs.started_on(ctx.tenant_id, server=SERVER, thread=thread)

    async def _about_the_run(self, ctx: RequestContext, one: Offered) -> None:
        if self._clock is None or self._ids is None:
            return
        about = f" — {one.subject}" if one.subject.strip() else ""
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=ctx.principal_id,
            text=(
                f"{one.title}{about}. A reply asks about the run this conversation already "
                "started; its card shows where it stands. Nothing new was started."
            ),
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": Said.NOTE,
                "workflow_id": one.workflow_id,
                "mail_thread": one.thread,
            },
        )
        logger.info(
            "%s: a reply on %s asks about its run, so nothing new was offered",
            ctx.tenant_id.value,
            one.thread,
        )

    async def _started(self, ctx: RequestContext, one: Offered) -> Offered:
        if (
            not one.sure
            or one.cannot_run
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
                values={
                    **{
                        name: one.aside[name]
                        for name in one.unasked
                        if name in one.aside and not is_secret_field(name)
                    },
                    **one.values,
                },
                live=True,
                allow_focus=False,
                conversation=(SERVER, one.thread),
                offer=one.named,
                mail=_envelope(one),
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
        await self._arrived(ctx, one, run)
        if self._attempts is not None:
            await self._attempts.execute(
                ctx,
                asked_for="start a job from a mail",
                came_of=DONE,
                about={"run": run.id, "workflow": one.workflow_id, "thread": one.thread},
            )
        return replace(one, started=True)

    async def _arrived(self, ctx: RequestContext, one: Offered, run: WorkflowRun) -> None:
        if self._clock is None or self._ids is None:
            return
        given = sourced(run.values, dict.fromkeys(one.answered, FROM_THE_REPLY), FROM_THE_MAIL)
        try:
            asked = await ReadThreads(self._uow).asking(ctx, one.thread)
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=ctx.principal_id,
                about=one.thread if asked is not None else "",
                text=(
                    f"A mail arrived{f' from {one.sender}' if one.sender else ''}: "
                    f"{_about(one.subject)}. It asks for {one.title}, so it is running now."
                    f"{given}"
                ),
                speaker=Speaker.ASSISTANT,
                decision={
                    "kind": Said.RUN,
                    "run_id": run.id,
                    "offer": run.offer or "",
                    "mail_thread": one.thread,
                },
            )
        except Exception:
            logger.exception(
                "%s: the thread could not be told %s started", ctx.tenant_id.value, run.id
            )

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

    async def _elsewhere(self, ctx: RequestContext, run: WorkflowRun) -> None:
        asking = Progress.of(run.progress).asking.get("id", "")
        async with self._uow as uow:
            await uow.tool_calls.remember(
                ctx.tenant_id,
                elsewhere_key(run.id, asking),
                tool=K_ELSEWHERE,
                at=datetime.now(tz=UTC),
            )
            await uow.commit()
        async with self._uow as uow:
            again = await uow.workflow_runs.get(ctx.tenant_id, run.id)
        if (
            again is not None
            and again.finished_at
            and self._clock is not None
            and self._ids is not None
        ):
            await SayWhatHappened(self._uow, self._clock, self._ids).answered_elsewhere(ctx, again)

    async def _answer_the_run(
        self, ctx: RequestContext, run: WorkflowRun, said: str, message: str
    ) -> None:
        asking = Progress.of(run.progress).asking
        async with self._uow as uow:
            key = elsewhere_key(run.id, asking.get("id", ""))
            await uow.tool_calls.forget(ctx.tenant_id, key)
            await uow.tool_calls.remember(ctx.tenant_id, key, tool=K_TAKEN, at=datetime.now(tz=UTC))
            await uow.commit()
        kind = asking.get("kind")
        if kind == "recipient":
            said = await self._address_the_operator_named(ctx, message)
        if kind not in ("value", "recipient") or not said:
            logger.info(
                "%s: a reply on %s's thread answers nothing: only a value is taken from mail, "
                "a recipient only from the operator's own, and whatever %s asks stands in "
                "the panel",
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

    async def _address_the_operator_named(self, ctx: RequestContext, message: str) -> str:
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return ""
        if not isinstance(said, dict) or said.get("sent") is not True:
            return ""
        reply = bool(said.get("in_reply_to") or said.get("references"))
        return one_address_in(str(said.get("body") or ""), reply=reply)

    async def _was_asked(self, ctx: RequestContext, thread: str) -> tuple[Pending | None, str]:
        """The question standing on a mail thread, and the address it was mailed
        to (empty while no mail went out): only that address answers it."""
        found = await ReadThreads(self._uow).asking(ctx, thread)
        if found is None:
            return None, ""
        (asked_of, *_) = (*addresses_in(asked_by_mail(found.messages, thread)), "")
        return waiting_on_mail(found.messages, thread), asked_of

    async def _carrying_on(
        self,
        ctx: RequestContext,
        message: str,
        back: WorkflowRun,
        said: str,
        thread: str,
        subject: str,
        titles: Mapping[str, str],
        held: Mapping[str, JobFacts] = MappingProxyType({}),
    ) -> Offered:
        # What a run still needs is unanswered, whatever the run last tried with.
        values = {name: one for name, one in back.values.items() if name not in back.needs}
        missing = list(back.needs)
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
        held: Mapping[str, JobFacts] = MappingProxyType({}),
    ) -> Offered:
        # A value the system refused is not an answer: it is asked for again.
        values = {name: one for name, one in asked.values.items() if name not in asked.refused}
        missing = [name for name in asked.missing if not values.get(name)]
        if asked.changing:
            # The system named no value: any one that changes answers, the rest stay.
            values = dict(asked.values)
            changed = changes(
                asked,
                await self._reply_says(
                    ctx, said, held.get(asked.workflow_id), missing, question=question(asked)
                ),
            )
            values |= changed
            missing = [] if changed else list(asked.missing)
        else:
            values |= await self._reply_says(
                ctx, said, held.get(asked.workflow_id), missing, question=question(asked)
            )
            missing = [name for name in missing if name not in values]
        if missing and self._gather is not None and not asked.changing:
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
        await self._the_question_is_answered(ctx, asked, values, missing, said_by=subject)
        return Offered(
            sure=asked.confirmed,
            message=message,
            workflow_id=asked.workflow_id,
            title=asked.title,
            values=values,
            missing=missing,
            thread=thread,
            subject=subject,
            offer=asked.offer,
            answered=[name for name in asked.missing if name not in missing],
        )

    async def _reply_says(
        self,
        ctx: RequestContext,
        said: str,
        job: JobFacts | None,
        wanted: Sequence[str],
        *,
        question: str = "",
    ) -> dict[str, str]:
        if not wanted or job is None or self._asker is None or not said.strip():
            return {}
        logins = await logins_of(self._uow, ctx.tenant_id)
        read = await understand(
            said, [candidate_of(job, logins=logins)], self._asker, question=question
        )
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
    ) -> None:
        if self._clock is None or self._ids is None:
            return
        try:
            filled = {name: values[name] for name in asked.missing if values.get(name)}
            named = ", ".join(
                f"{name} {quoted(value, FROM_THE_REPLY)}" for name, value in filled.items()
            )
            about = f" to {_about(said_by)}" if said_by.strip() else ""
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
                changing=asked.changing,
            )
            said = f"A reply{about} answered: {named or 'nothing I could use'}." + (
                f" {question(still)}" if missing else ""
            )
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=ctx.principal_id,
                text=said,
                speaker=Speaker.ASSISTANT,
                about=asked.mail_thread,
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
                        **({"changing": True} if still.changing else {}),
                    }
                    if missing
                    else {
                        "kind": Said.NOTE,
                        "workflow_id": still.workflow_id,
                        "mail_thread": still.mail_thread,
                    }
                ),
            )
        except Exception:
            logger.exception("the answered question could not be closed")

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
        reach: _Reach,
    ) -> AsyncIterator[str]:
        pages = 1
        while True:
            for message in arrivals:
                if await self._caught_up_to(ctx, message, now=now):
                    reach.whole = not reach.busy
                    return
                took = await self._take(ctx, message, now=now)
                reach.busy += took is None
                if took:
                    yield message
            if not more:
                reach.whole = not reach.busy
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
        return [
            str(row["id"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        ][:limit], _page_of(answered.text)

    async def _body(self, ctx: RequestContext, message: str) -> _Mail:
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return _Mail()
        if not isinstance(said, dict):
            return _Mail()
        whole = " ".join(
            str(said.get(part) or "").strip() for part in ("subject", "body", "snippet")
        )
        whole = " ".join(whole.split())
        return _Mail(
            said=whole[:K_TEXT],
            thread=str(said.get("thread_id") or ""),
            subject=" ".join(str(said.get("subject") or "").split())[:K_SUBJECT],
            sent_to=sent_to_others(
                *(str(said.get(part) or "") for part in ("from", "to", "cc", "mailbox"))
            ),
            marker=str(said.get("marker") or ""),
            sender=" ".join(str(said.get("from") or "").split())[:K_SUBJECT],
            arrived=_when(str(said.get("date") or "")),
        )

    async def _conversation(
        self, ctx: RequestContext, thread: str, message: str
    ) -> tuple[str, str]:
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_thread", {"id": thread}
        )
        try:
            said = None if answered.failed else json.loads(answered.text)
        except ValueError:
            said = None
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list):
            # Unread is not "this mail alone": that would make a quoted reply fresh.
            raise ToolsUnavailable(f"thread {thread} could not be read")
        rows = [one for one in rows if isinstance(one, dict)]
        whole = _joined(rows)[-K_THREAD:]
        return whole, _joined([one for one in rows if one.get("id") != message])

    async def _take(self, ctx: RequestContext, message: str, *, now: datetime) -> bool | None:
        tenant, kept, reading = ctx.tenant_id, mail_key(message), _reading_key(message)
        async with self._uow as uow:
            if await uow.tool_calls.held(tenant, kept, since=now - K_REMEMBER):
                return False
            if not await uow.tool_calls.remember(
                tenant, reading, tool=K_READ_TOOL, at=now, stale_after=K_LEASE
            ):
                return None
            if await uow.tool_calls.held(tenant, kept, since=now - K_REMEMBER):
                await uow.tool_calls.forget(tenant, reading)
                await uow.commit()
                return False
            await uow.commit()
        return True

    async def _keep(self, ctx: RequestContext, message: str, *, now: datetime) -> None:
        async with self._uow as uow:
            await uow.tool_calls.remember(
                ctx.tenant_id,
                mail_key(message),
                tool=K_READ_TOOL,
                at=now,
                stale_after=K_REMEMBER,
            )
            await uow.tool_calls.forget(ctx.tenant_id, _reading_key(message))
            await uow.commit()

    async def _release(self, ctx: RequestContext, message: str) -> None:
        async with self._uow as uow:
            await uow.tool_calls.forget(ctx.tenant_id, _reading_key(message))
            await uow.commit()

    async def _caught_up_to(self, ctx: RequestContext, message: str, *, now: datetime) -> bool:
        async with self._uow as uow:
            return await uow.tool_calls.held(
                ctx.tenant_id, _caught_key(ctx, message), since=now - K_REMEMBER
            )

    async def _caught_up(self, ctx: RequestContext, message: str, *, now: datetime) -> None:
        async with self._uow as uow:
            await uow.tool_calls.remember(
                ctx.tenant_id,
                _caught_key(ctx, message),
                tool="the newest mail a whole look reached",
                at=now,
                stale_after=K_REMEMBER,
            )
            await uow.commit()


class Unread(Exception):
    pass


class _Theirs(Exception):
    pass


@dataclass(slots=True)
class _Look:
    read: int = 0
    unsure: int = 0
    theirs: int = 0
    spent: Answer = field(default_factory=Answer)
    asks_nothing: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Reach:
    whole: bool = False
    busy: int = 0


@dataclass(frozen=True, slots=True)
class _Mail:
    said: str = ""
    thread: str = ""
    subject: str = ""
    sent_to: tuple[str, ...] = ()
    marker: str = ""
    sender: str = ""
    arrived: str = ""


@dataclass(frozen=True, slots=True)
class _Known:
    workflows: list[Workflow]
    asker: Asker
    facts: tuple[JobFacts, ...]
    titles: Mapping[str, str]
    held: Mapping[str, JobFacts]
    held_by: Mapping[str, int]
    now: datetime
    logins: Logins


def _joined(rows: Sequence[Mapping[str, object]]) -> str:
    whole = " ".join(
        " ".join(str(one.get(part) or "") for part in ("subject", "body")) for one in rows
    )
    return " ".join(whole.split())


def _page_of(answered: str) -> str:
    try:
        said = json.loads(answered)
    except ValueError:
        return ""
    more = said.get("next_page") if isinstance(said, dict) else None
    return more if isinstance(more, str) and K_PAGE_TOKEN.fullmatch(more) else ""


def _when(date: str) -> str:
    try:
        return parsedate_to_datetime(date).isoformat() if date.strip() else ""
    except (TypeError, ValueError):
        return ""


def _envelope(one: Offered) -> dict[str, str]:
    return {
        name: value
        for name, value in (
            ("subject", one.subject),
            ("sender", one.sender),
            ("arrived", one.arrived),
        )
        if value
    }


def _about(subject: str) -> str:
    return f"'{subject}'" if subject.strip() else "a mail with no subject"


def _came_to(one: Offered) -> str:
    if one.started:
        return f"started {one.title}; its card on Home shows how it goes"
    if one.asked:
        return f"{one.title}, asked about here"
    return f"offered {one.title}; its card is on Home"


def _reading_key(message: str) -> str:
    return f"reading:{message}"


def _caught_key(ctx: RequestContext, message: str) -> str:
    return f"caught:{ctx.principal_id.value}:{message}"


def _sentence(offered: Sequence[Offered], read: int, unsure: int = 0, theirs: int = 0) -> str:
    if not read:
        return "no mail has arrived since the last look"
    if not offered and theirs:
        return f"read {read}, and {theirs} answers a run another operator started"
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
