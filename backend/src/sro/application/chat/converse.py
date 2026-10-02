from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sro.application.chat.mailbox import mail_key
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.reading_an_answer import IsItAnAnswer
from sro.application.chat.understand import Understood
from sro.application.connection.sign_in import logins_of
from sro.application.context import RequestContext
from sro.application.execution.derived_read import Asked, AskTheSystem
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.intent.match import writes
from sro.application.intent.narrow import NarrowARead, NeedToAsk, value_key
from sro.application.intent.next_steps import SuggestNext
from sro.application.intent.resolve import Resolution, ResolveIntent
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.lookup.answer import as_seen
from sro.application.lookup.look_it_up import LookItUp, what_was_found
from sro.application.lookup.plan_lookups import PlanLookups
from sro.application.lookup.run_lookups import (
    K_WHILE_TALKING,
    Answers,
    Looked,
    RunLookups,
)
from sro.application.observation.record_attempt import RecordAttempt
from sro.application.ports.http import TargetUnreachable
from sro.application.ports.model import AskerUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.shared.refusals import OverCap, RunRefused
from sro.domain.chat.asking import (
    ASKS,
    FROM_THE_CHAT,
    FROM_THE_MAIL,
    FROM_THE_REQUEST,
    NEEDS,
    Pending,
    answered,
    asked_by_mail,
    asked_under,
    asking_state,
    cannot_without,
    envelope_of,
    let_go,
    named_in,
    of_the_offer,
    offered_job,
    pending_job,
    question,
    said_yes,
    sourced,
    too_long_for,
    turned_down,
)
from sro.domain.chat.brain_turn import K_HISTORY, Origin
from sro.domain.chat.request import Candidate
from sro.domain.chat.standing import last_run, of_a_mail_run, of_the_run, stands
from sro.domain.chat.thread import Message, MessageId, Said, Speaker, Thread, ThreadId
from sro.domain.execution.compose import alias_map
from sro.domain.execution.field_classes import field_classes
from sro.domain.execution.mail_job import (
    DRAFT_QUESTIONS,
    LOOK_IN_THE_MAIL,
    built_in,
    built_ins,
)
from sro.domain.execution.progress import Progress
from sro.domain.execution.run import Run, RunId, RunStatus, StepDisposition
from sro.domain.execution.workflow_run import OfferTaken, WorkflowRun, answers_for
from sro.domain.lookup.asking import is_a_question
from sro.domain.observation.attempts import DONE, FAILED, REFUSED
from sro.domain.shared.errors import Conflict, DomainError
from sro.domain.skill.skill import Skill

if TYPE_CHECKING:
    from sro.application.chat.brain import Brain
    from sro.application.chat.feedback import RecordFeedback
    from sro.application.chat.from_the_mail import FromTheMail
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from sro.application.runtime.answer_run import AnswerRun

logger = logging.getLogger(__name__)

K_CLOSED = "That question is no longer open, so nothing was done."

K_NOT_YOURS = "That question was asked of somebody else, so nothing was done."


class StartThread:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext) -> Thread:
        thread = Thread(
            id=self._ids.new_thread_id(),
            tenant_id=ctx.tenant_id,
            opened_by=ctx.principal_id,
            opened_at=self._clock.now(),
        )
        async with self._uow as uow:
            await uow.threads.add(thread)
            await uow.commit()
        return thread


class _NotAsked: ...


class _Closed(Exception): ...


NOT_ASKED = _NotAsked()

K_MAIL_RUNS = 20

K_MAIL_DAY = timedelta(days=1)

K_LOOK = Candidate(
    LOOK_IN_THE_MAIL, "Look in the mail for new work now", fields=(), aliases={}, seen={}
)


class Converse:
    def __init__(
        self,
        uow: UnitOfWork,
        resolver: ResolveIntent,
        clock: Clock,
        ids: IdFactory,
        execute: ExecuteSkill | None = None,
        narrow: NarrowARead | None = None,
        ask: AskTheSystem | None = None,
        questions: AskAbout | None = None,
        suggest: SuggestNext | None = None,
        reads_jobs: ReadChat | None = None,
        can_gather: bool = False,
        answers: IsItAnAnswer | None = None,
        plan_lookups: PlanLookups | None = None,
        run_lookups: RunLookups | None = None,
        answer_run: AnswerRun | None = None,
        start: StartWorkflowRun | None = None,
        spawn: Callable[[Coroutine[object, object, None]], None] | None = None,
        attempts: RecordAttempt | None = None,
        look: FromTheMail | None = None,
        brain: Brain | None = None,
        brain_tenants: frozenset[str] = frozenset(),
        brain_shadow_tenants: frozenset[str] = frozenset(),
        feedback: RecordFeedback | None = None,
    ) -> None:
        self._uow = uow
        self._feedback = feedback
        self._brain = brain
        self._brain_tenants = brain_tenants
        self._brain_shadow_tenants = brain_shadow_tenants
        self._look = look
        self._answer_run = answer_run
        self._resolver = resolver
        self._reads_jobs = reads_jobs
        self._answers = answers
        self._clock = clock
        self._ids = ids
        self._execute = execute
        self._narrow = narrow
        self._ask = ask
        self._questions = questions
        self._suggest = suggest
        self._can_gather = can_gather
        self._plan_lookups = plan_lookups
        self._run_lookups = run_lookups
        self._start = start
        self._spawn = spawn
        self._attempts = attempts

    async def note(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> None:
        async with self._uow as uow:
            thread = _opened_by_the_caller(ctx, await uow.threads.get(ctx.tenant_id, thread_id))
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=text,
                    said_at=self._clock.now(),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()

    async def execute(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
        run_id: RunId | None = None,
        answering: str | None = None,
    ) -> Thread:
        if run_id is not None:
            return await self._said_to_a_run(ctx, thread_id=thread_id, text=text, run_id=run_id)
        async with self._uow as uow:
            before = await uow.threads.get(ctx.tenant_id, thread_id)
        said_before = before.messages
        try:
            _opened_by_the_caller(ctx, before)
        except Conflict:
            told = None
            if answering is None and pending_job(said_before) is None:
                told = await self._what_stands(ctx, before)
            self._told(before, text, told or K_NOT_YOURS)
            return before
        run_asks = asked_under(said_before, answering)
        answer = self._answer_run
        if run_asks is not None and answer and await self._open_in_words(ctx, run_asks):
            asks = Pending("", "", {}, (str((run_asks.decision or {}).get("asks")),))
            answered_it, about = await self._is_it_an_answer(ctx, asks, text)
            if answered_it is not None:
                return await self._answer_the_run(
                    ctx, answer, thread_id=thread_id, text=text, value=answered_it, asked=run_asks
                )
            if about != "another_task":
                await self._also_said(ctx, thread_id=thread_id, text=text)
                return await self._ask_the_run_again(ctx, thread_id=thread_id, asked=run_asks)
            return await self._carry_on_under(
                ctx,
                thread_id=thread_id,
                text=text,
                system=system,
                parameters=parameters,
                ask_again=lambda: self._ask_the_run_again(ctx, thread_id=thread_id, asked=run_asks),
            )
        if (
            answering is not None
            and pending_job(said_before, answering) is None
            and offered_job(said_before, answering) is None
        ):
            return await self._only_said(ctx, thread_id=thread_id, text=text)
        asked = asked_under(said_before, answering)
        waiting = await self._still_wanted(ctx, pending_job(said_before, answering))
        if waiting is not None and asked is not None:
            answered_it, about = await self._is_it_an_answer(ctx, waiting, text)
            if answered_it is not None:
                return await self._answer_the_question(
                    ctx,
                    thread_id=thread_id,
                    text=answered_it,
                    pending=waiting,
                    asked=asked.id,
                    answering=answering,
                )
            if about != "another_task":
                await self._also_said(ctx, thread_id=thread_id, text=text)
                return await self._ask_it_again(
                    ctx,
                    thread_id=thread_id,
                    pending=waiting,
                    asked=asked,
                    said_before=said_before,
                )
            return await self._carry_on_under(
                ctx,
                thread_id=thread_id,
                text=text,
                system=system,
                parameters=parameters,
                ask_again=lambda: self._ask_it_again(
                    ctx, thread_id=thread_id, pending=waiting, asked=asked, said_before=said_before
                ),
            )
        return await self._carry_on(
            ctx,
            thread_id=thread_id,
            text=text,
            system=system,
            parameters=parameters,
            answering=answering,
        )

    async def _carry_on_under(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None,
        parameters: dict[str, str] | None,
        ask_again: Callable[[], Coroutine[object, object, Thread]],
    ) -> Thread:
        placed = None if self._the_brain(ctx) else await self._placed_by_the_rig(ctx, text)
        waits = placed is not None and not placed.cannot_run
        if waits:
            await ask_again()
        carried = await self._carry_on(
            ctx,
            thread_id=thread_id,
            text=text,
            system=system,
            parameters=parameters,
            placed=placed,
            standing=True,
        )
        return carried if waits else await ask_again()

    async def _open_in_words(self, ctx: RequestContext, asked: Message) -> bool:
        decision = asked.decision or {}
        if decision.get("kind") != "run_asks" or decision.get("asks") not in DRAFT_QUESTIONS:
            return False
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, str(decision.get("run_id") or ""))
        asking = Progress.of(run.progress).asking if run is not None else {}
        return asking.get("id") == decision.get("question_id") and not asking.get("answered")

    async def _answer_the_run(
        self,
        ctx: RequestContext,
        answer: AnswerRun,
        *,
        thread_id: ThreadId,
        text: str,
        value: str,
        asked: Message,
    ) -> Thread:
        decision = asked.decision or {}
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=self._clock.now(),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        said = "Got it -- the run goes on with that."
        try:
            await answer.execute(
                ctx,
                run_id=str(decision.get("run_id") or ""),
                question_id=str(decision.get("question_id") or ""),
                value=value,
            )
        except Conflict as refused:
            said = f"{refused}; the question still stands."
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _ask_the_run_again(
        self, ctx: RequestContext, *, thread_id: ThreadId, asked: Message
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=asked.text,
                    said_at=self._clock.now(),
                    decision=dict(asked.decision or {}),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _only_said(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, said: str = K_CLOSED
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            self._told(thread, text, said)
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    def _told(
        self, thread: Thread, text: str, said: str, decision: dict[str, object] | None = None
    ) -> None:
        for speaker, words, decided in (
            (Speaker.OPERATOR, text, None),
            (Speaker.ASSISTANT, said, decision),
        ):
            if not words:
                continue
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=speaker,
                    text=words,
                    said_at=self._clock.now(),
                    decision=decided or {},
                )
            )

    async def _carry_on(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
        placed: Understood | _NotAsked | None = NOT_ASKED,
        standing: bool = False,
        answering: str | None = None,
    ) -> Thread:
        async with self._uow as uow:
            said_before = (await uow.threads.get(ctx.tenant_id, thread_id)).messages
        offered = offered_job(said_before, answering)
        asked = asked_under(said_before, answering)
        if offered is not None and asked is not None and (said_yes(text) or let_go(text)):
            return await self._say_yes_to_it(
                ctx,
                thread_id=thread_id,
                text=text,
                offered=offered,
                asked=asked.id,
                answering=answering,
            )
        if offered is not None and answering is not None:
            return await self._only_said(
                ctx,
                thread_id=thread_id,
                text=text,
                said=f"Say yes to run {offered.title}, or no to leave it.",
            )
        if (brain := self._the_brain(ctx)) is not None:
            return await self._brain_turn(
                brain, ctx, thread_id=thread_id, text=text, system=system, answering=answering
            )
        if self._brain is None or ctx.tenant_id.value not in self._brain_shadow_tenants:
            return await self._the_chain(
                ctx,
                thread_id=thread_id,
                text=text,
                system=system,
                parameters=parameters,
                placed=placed,
                standing=standing,
            )
        # The chain answers; the brain reads the same message off the request path, and when the
        # chain's reply is written the two are compared (see `_compared`).
        written: asyncio.Future[Thread | None] = asyncio.get_running_loop().create_future()
        self._shadow(ctx, thread_id, said_before, text, system, answering, written)
        answered: Thread | None = None
        try:
            answered = await self._the_chain(
                ctx,
                thread_id=thread_id,
                text=text,
                system=system,
                parameters=parameters,
                placed=placed,
                standing=standing,
            )
            return answered
        finally:
            written.set_result(answered)

    async def _the_chain(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None,
        parameters: dict[str, str] | None,
        placed: Understood | _NotAsked | None,
        standing: bool,
    ) -> Thread:
        if isinstance(placed, _NotAsked):
            placed = await self._placed_by_the_rig(ctx, text)
        if placed is not None:
            return await self._say_the_job(ctx, thread_id=thread_id, text=text, placed=placed)
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
        told: str | None = None

        async def something_stands() -> bool:
            nonlocal told
            if standing:
                return True
            told = await self._what_stands(ctx, thread)
            return told is not None

        resolution = await self._resolver.execute(
            ctx,
            utterance=text,
            system=system,
            parameters={**_gathered(thread, _awaiting(thread)), **(parameters or {})},
            after=_last_asked(thread),
            pinned=_awaiting(thread),
            standing=something_stands,
        )

        looked = await self._look_it_up(ctx, text, resolution)
        if looked is not None:
            return await self._say_what_was_found(ctx, thread_id=thread_id, text=text, found=looked)

        if resolution.about_what_stands and standing:
            return await self._also_said(ctx, thread_id=thread_id, text=text)
        if resolution.about_what_stands and told is not None:
            return await self._only_said(ctx, thread_id=thread_id, text=text, said=told)

        narrowed = await self._narrowed(ctx, resolution)
        run = None if narrowed else await self._answer_now(ctx, resolution)

        if resolution.proposal is not None and (
            standing or await self._question_stands(ctx, thread_id)
        ):
            return await self._also_said(ctx, thread_id=thread_id, text=text)

        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=(
                        _what_it_found(narrowed, resolution)
                        if narrowed and narrowed.answer
                        else narrowed.detail
                        if narrowed
                        else _reply(resolution) + _why_it_failed(run)
                    ),
                    said_at=self._clock.now(),
                    decision=_decision(
                        resolution,
                        run,
                        narrowed,
                        await self._next_steps(ctx, resolution, run, narrowed),
                    ),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    def _the_brain(self, ctx: RequestContext) -> Brain | None:
        return self._brain if ctx.tenant_id.value in self._brain_tenants else None

    def _shadow(
        self,
        ctx: RequestContext,
        thread_id: ThreadId,
        said_before: Sequence[Message],
        text: str,
        system: str | None,
        answering: str | None,
        written: asyncio.Future[Thread | None],
    ) -> None:
        if self._brain is not None and self._spawn is not None:
            self._spawn(
                self._compared(
                    self._brain,
                    ctx,
                    thread_id,
                    written,
                    message=text,
                    history=_history(said_before),
                    asking=_open_question(said_before, answering),
                    page=system or "",
                )
            )

    async def _compared(
        self,
        brain: Brain,
        ctx: RequestContext,
        thread_id: ThreadId,
        written: asyncio.Future[Thread | None],
        *,
        message: str,
        history: list[str],
        asking: str,
        page: str,
    ) -> None:
        """The dry brain turn, then, once the chain's reply stands, what the two did compared.
        Off the request path: it raises nothing and holds nothing up."""
        reply = await brain.shadow(
            ctx, message=message, history=history, origin=Origin("chat"), asking=asking, page=page
        )
        try:
            answered = await written
            if reply is None or answered is None or self._feedback is None:
                return
            said = answered.messages
            spoke = [n for n, one in enumerate(said) if one.speaker is Speaker.OPERATOR]
            if not spoke:
                return
            chain = [one for one in said[spoke[-1] + 1 :] if one.speaker is Speaker.ASSISTANT]
            await self._feedback.turn(
                ctx,
                thread_id=thread_id.value,
                operator=said[spoke[-1]],
                reply=reply,
                mode="shadow",
                chain=chain[-1] if chain else None,
            )
        except Exception:
            logger.exception("brain shadow comparison failed")

    async def _brain_turn(
        self,
        brain: Brain,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None,
        answering: str | None,
    ) -> Thread:
        said = (await self._also_said(ctx, thread_id=thread_id, text=text)).messages
        said_before = said[:-1]
        reply = await brain.turn(
            ctx,
            message=text,
            history=_history(said_before),
            origin=Origin("chat"),
            asking=_open_question(said_before, answering),
            page=system or "",
            # One message, one run for the same job and values: the offer's uniqueness.
            offer=f"chat:{said[-1].id.value}",
        )
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            # Every run the turn started keeps its card; the turn's own words close it.
            cards = [(r.said, r.decision) for _, r in reply.steps if r.decision]
            for words, decision in cards[:-1]:
                self._told(thread, "", words, decision)
            self._told(thread, "", reply.said, cards[-1][1] if cards else None)
            await uow.threads.save(thread)
            await uow.commit()
        if self._feedback is not None:
            await self._feedback.turn(
                ctx, thread_id=thread_id.value, operator=said[-1], reply=reply, mode="live"
            )
        if self._attempts is not None:
            for call, result in reply.steps:
                if call.tool in _STARTS:
                    await self._attempts.execute(
                        ctx,
                        asked_for=_STARTS[call.tool],
                        came_of=DONE if result.ok else REFUSED,
                        why=result.error,
                        about={
                            "run": str((result.data or {}).get("run_id") or ""),
                            "workflow": str(call.args.get("job_id") or ""),
                            "thread": thread_id.value,
                        },
                    )
        return thread

    async def _still_wanted(self, ctx: RequestContext, waiting: Pending | None) -> Pending | None:
        if waiting is None or not waiting.workflow_id:
            return waiting
        async with self._uow as uow:
            job = await uow.workflows.get(ctx.tenant_id, waiting.workflow_id)
            aliases = (
                await uow.workflows.aliases_for(ctx.tenant_id, waiting.workflow_id) if job else ()
            )
        if job is None or not job.parameters:
            return waiting
        fields = field_classes(job, {}, {})
        known = Candidate(job.id, job.title, fields, alias_map(aliases), {})
        wanted = {one.name for one in fields if (one.kind == "required" or waiting.changing)}
        still = tuple(name for name in waiting.missing if name in wanted or name in waiting.refused)
        return replace(waiting, missing=still, known=known) if still else None

    async def _what_stands(self, ctx: RequestContext, thread: Thread) -> str | None:
        now = self._clock.now()
        if (run_id := last_run(thread.messages)) is not None:
            async with self._uow as uow:
                run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
                seen = run is not None and answers_for(
                    run, ctx.principal_id.value, opened_by=thread.opened_by.value
                )
                job = (
                    run.pinned or await uow.workflows.get(ctx.tenant_id, run.workflow_id)
                    if run is not None and seen
                    else None
                )
            if run is not None and seen and stands(run, now):
                return of_the_run(run, job.title if job is not None else "The run", now)
        offer = offered_job(thread.messages) if thread.opened_by == ctx.principal_id else None
        return of_the_offer(offer) if offer is not None else None

    async def _question_stands(self, ctx: RequestContext, thread_id: ThreadId) -> bool:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
        return pending_job(thread.messages) is not None

    async def _also_said(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=self._clock.now(),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _ask_it_again(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        pending: Pending,
        asked: Message,
        said_before: Sequence[Message] = (),
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=(
                        f"{_nothing_back(said_before)}{question(pending)}{_the_way_out(pending)}"
                    ),
                    said_at=self._clock.now(),
                    decision={
                        "kind": NEEDS,
                        "workflow_id": pending.workflow_id,
                        "title": pending.title,
                        "values": dict(pending.values),
                        "items": [dict(one) for one in pending.items],
                        "missing": list(pending.missing),
                        "watched": pending.watched,
                        "limits": dict(pending.limits),
                        "from_step": pending.from_step,
                        "mail_thread": pending.mail_thread,
                        "offer": _chained(asked),
                        **asking_state(pending),
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _is_it_an_answer(
        self, ctx: RequestContext, pending: Pending, text: str
    ) -> tuple[str | None, str]:
        if let_go(text) or self._answers is None:
            return text, ""
        if named_in(pending, text):
            return text, ""
        read = await self._answers.execute(ctx, pending, text)
        if read.answers:
            return read.value or text, ""
        logger.info(
            "%s: %r is not an answer to %s (%s)",
            ctx.tenant_id.value,
            text[:40],
            pending.asking_for,
            read.why[:80],
        )
        return None, read.about

    async def _answer_the_question(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        pending: Pending,
        asked: MessageId,
        answering: str | None,
    ) -> Thread:
        logins = await logins_of(self._uow, ctx.tenant_id)
        async with self._uow as uow:
            thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
            still = asked_under(thread.messages, answering)
            offer = _offer_of(thread.messages, asked)
            if still is None or still.id != asked:
                self._closed(thread, text, offer)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
            filled = None if let_go(text) else answered(pending, text, logins)
            if filled is None or filled.without or not filled.ready:
                said, decision = _not_yet(pending, filled, text, offer)
                self._told(thread, text, said, decision)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
        return await self._start_it(
            ctx,
            thread_id=thread_id,
            text=text,
            asked=asked,
            answering=answering,
            job=filled,
            offer=offer,
            mail=envelope_of(thread.messages, filled.mail_thread),
            answered=[name for name in pending.missing if filled.values.get(name)],
        )

    async def _say_yes_to_it(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        offered: Pending,
        asked: MessageId,
        answering: str | None,
    ) -> Thread:
        ready = offered.ready or self._can_gather
        async with self._uow as uow:
            thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
            still = asked_under(thread.messages, answering)
            offer = _offer_of(thread.messages, asked)
            if still is None or still.id != asked:
                self._closed(thread, text, offer)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
            if let_go(text) or not ready:
                said = question(offered)
                decision: dict[str, object] = {
                    **_to_run(offered, offer, self._can_gather),
                    "kind": NEEDS,
                }
                if let_go(text):
                    said = f"Left {offered.title}."
                    decision = {
                        "kind": Said.NOTE,
                        "workflow_id": offered.workflow_id,
                        "mail_thread": offered.mail_thread,
                    }
                self._told(thread, text, said, decision)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
        return await self._start_it(
            ctx,
            thread_id=thread_id,
            text=text,
            asked=asked,
            answering=answering,
            job=replace(offered, missing=()),
            offer=offer,
            mail=envelope_of(thread.messages, offered.mail_thread),
        )

    async def _start_it(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        asked: MessageId | None,
        answering: str | None,
        job: Pending,
        offer: str,
        mail: Mapping[str, str] | None = None,
        answered: Sequence[str] = (),
    ) -> Thread:
        decision = _to_run(job, offer, self._can_gather)
        running = f"Running {job.title} now." + sourced(
            job.values,
            dict.fromkeys(answered, FROM_THE_CHAT),
            FROM_THE_MAIL if job.mail_thread else FROM_THE_REQUEST,
        )
        wrote: list[Thread] = []

        async def say_it(uow: UnitOfWork, run: WorkflowRun) -> None:
            wrote.append(
                await self._answered_in(
                    uow,
                    ctx,
                    thread_id=thread_id,
                    text=text,
                    asked=asked,
                    answering=answering,
                    said=running,
                    decision={**decision, "resume": True, "run_id": run.id},
                )
            )

        try:
            if self._start is None or (self._spawn is None and not self._start.runs_on_steel(ctx)):
                raise RunRefused("this process cannot start a run")
            run = await self._start.execute(
                ctx,
                workflow_id=job.workflow_id,
                device_id=None,
                values=job.values,
                items=job.items,
                live=True,
                allow_focus=True,
                watched=job.watched,
                from_step=job.from_step,
                conversation=(self._start.mail_server(ctx), job.mail_thread),
                offer=offer,
                mail=mail,
                then=say_it,
            )
        except _Closed:
            return await self._closed_now(ctx, thread_id, text, offer)
        except (DomainError, RunRefused, OverCap, AskerUnavailable) as refusal:
            # A press on this offer's card got there first: the yes is answered
            # with that run, which the panel then watches.
            taken = refusal.run_id if isinstance(refusal, OfferTaken) else ""
            try:
                async with self._uow as uow:
                    thread = await self._answered_in(
                        uow,
                        ctx,
                        thread_id=thread_id,
                        text=text,
                        asked=asked,
                        answering=answering,
                        said=(
                            f"{job.title} is already running."
                            if taken
                            else f"Nothing was started: {refusal}."
                        ),
                        decision={**decision, "resume": True, "run_id": taken}
                        if taken
                        else decision,
                    )
                    await uow.commit()
            except _Closed:
                return await self._closed_now(ctx, thread_id, text, offer)
            await self._attempted(ctx, REFUSED, job, thread_id, why=str(refusal))
            return thread
        if run.executor == "steel":
            if not await self._start.start_on_steel(ctx, run):
                return await self._did_not_start(ctx, thread_id, job, run)
        elif self._spawn is not None:
            self._spawn(self._start.perform(ctx, run))
        await self._attempted(ctx, DONE, job, thread_id, run=run.id)
        return wrote[0]

    async def _did_not_start(
        self, ctx: RequestContext, thread_id: ThreadId, job: Pending, run: WorkflowRun
    ) -> Thread:
        async with self._uow as uow:
            saved = await uow.workflow_runs.get(ctx.tenant_id, run.id)
            why = saved.steps[-1].reason if saved is not None and saved.steps else ""
            thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=(
                        f"{job.title} did not start: {why or 'it could not be handed on'}. "
                        "Nothing was done; ask for it again to retry."
                    ),
                    said_at=self._clock.now(),
                    decision={
                        "kind": Said.NOTE,
                        "workflow_id": job.workflow_id,
                        "mail_thread": job.mail_thread,
                        "run_id": run.id,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        await self._attempted(ctx, FAILED, job, thread_id, run=run.id, why=why)
        return thread

    async def _attempted(
        self,
        ctx: RequestContext,
        came_of: str,
        job: Pending,
        thread_id: ThreadId,
        *,
        run: str = "",
        why: str = "",
    ) -> None:
        if self._attempts is not None:
            await self._attempts.execute(
                ctx,
                asked_for="start a job from chat",
                came_of=came_of,
                why=why,
                about={"run": run, "workflow": job.workflow_id, "thread": thread_id.value},
            )

    def _closed(self, thread: Thread, text: str, offer: str) -> None:
        ran = next(
            (
                str(said["run_id"])
                for message in reversed(thread.messages)
                if (said := message.decision or {}).get("offer") == offer and said.get("run_id")
            ),
            "",
        )
        self._told(thread, text, K_CLOSED, {"run_id": ran} if ran else None)

    async def _closed_now(
        self, ctx: RequestContext, thread_id: ThreadId, text: str, offer: str
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
            self._closed(thread, text, offer)
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _answered_in(
        self,
        uow: UnitOfWork,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        asked: MessageId | None,
        answering: str | None,
        said: str,
        decision: dict[str, object],
    ) -> Thread:
        thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
        still = asked_under(thread.messages, answering)
        if asked is not None and (still is None or still.id != asked):
            raise _Closed
        if asker := asked_by_mail(thread.messages, str(decision.get("mail_thread") or "")):
            said = f"{said} {asker} was asked by mail before this answer came."
        self._told(thread, text, said, decision)
        await uow.threads.save(thread)
        return thread

    async def _placed_by_the_rig(self, ctx: RequestContext, text: str) -> Understood | None:
        if self._reads_jobs is None:
            return None
        try:
            placed = await self._reads_jobs.execute(
                ctx, utterance=text, also=(K_LOOK,) if self._look is not None else ()
            )
        except Exception:
            logger.info("the rig could not place %r; asking the skills instead", text[:40])
            return None
        return placed if placed.workflow_id else None

    async def _say_the_job(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, placed: Understood
    ) -> Thread:
        if placed.workflow_id == LOOK_IN_THE_MAIL and self._look is not None:
            return await self._look_in_the_mail(ctx, self._look, thread_id=thread_id, text=text)
        mail = built_in(placed.workflow_id or "", ctx.tenant_id.value)
        if mail is not None and placed.sure and not placed.cannot_run and not placed.missing:
            request = Message(
                id=self._ids.new_message_id(),
                speaker=Speaker.OPERATOR,
                text=text,
                said_at=self._clock.now(),
            )
            async with self._uow as uow:
                thread = await uow.threads.get(ctx.tenant_id, thread_id)
                thread.say(request)
                await uow.threads.save(thread)
                await uow.commit()
            return await self._start_it(
                ctx,
                thread_id=thread_id,
                text="",
                asked=None,
                answering=None,
                job=Pending(
                    workflow_id=mail.id,
                    title=mail.title,
                    values=dict(placed.values),
                    missing=(),
                    items=tuple(dict(one) for one in placed.items),
                ),
                offer=request.id.value,
            )
        async with self._uow as uow:
            known = {
                one.id: one
                for one in (
                    *await uow.workflows.known(ctx.tenant_id),
                    *built_ins(ctx.tenant_id.value),
                )
            }
            title = known[placed.workflow_id].title if placed.workflow_id in known else "That job"
            things = len(placed.items)
            if not placed.sure:
                titles = [title, *[known[one].title for one in placed.also if one in known]]
                said = f"Did you mean {' or '.join(titles)}? Say which and I will set it up."
                return await self._ask_which(
                    ctx,
                    thread_id=thread_id,
                    text=text,
                    said=said,
                    choices=[placed.workflow_id, *placed.also],
                    titles=titles,
                )
            if placed.cannot_run:
                said = (
                    f"{title} does that, but it cannot run yet: "
                    f"{'; '.join(placed.cannot_run)}. Nothing was started."
                )
            elif placed.refused:
                said = (
                    f"{title} does that, but "
                    + "; ".join(
                        f"the {name} you gave is {why}" for name, why in placed.refused.items()
                    )
                    + " — give me another and I will run it."
                )
            elif placed.missing and self._can_gather:
                said = (
                    f"{title} does that. I will look in your mail for "
                    f"{', '.join(placed.missing)} — say the word and I will run it,"
                    " or type them here to say which."
                )
            elif placed.missing:
                said = (
                    f"{title} does that. I still need {', '.join(placed.missing)}"
                    " — give me that and I will run it."
                )
            elif things > 1:
                said = f"{title}, for {things} things — say the word and I will do them."
            else:
                said = f"{title} does that — say the word and I will run it."
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                    decision={
                        "kind": Said.NOTE,
                        "workflow_id": placed.workflow_id,
                        "cannot_run": list(placed.cannot_run),
                    }
                    if placed.cannot_run
                    else {
                        "kind": "job",
                        "workflow_id": placed.workflow_id,
                        "title": title,
                        "values": dict(placed.values),
                        "items": [dict(one) for one in placed.items],
                        "missing": list(placed.missing),
                        "can_find": self._can_gather,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _look_in_the_mail(
        self, ctx: RequestContext, look: FromTheMail, *, thread_id: ThreadId, text: str
    ) -> Thread:
        await self._also_said(ctx, thread_id=thread_id, text=text)
        started: set[str] = set()
        try:
            looked = await look.execute(ctx)
            said = looked.said()
            started = {mail_key(one.message) for one in looked.offered}
        except (OverCap, AskerUnavailable) as refused:
            said = f"I could not look in the mail: {refused}."
        earlier = await self._mail_runs(ctx, besides=started)
        if earlier:
            said += "\nFrom the mail earlier:\n" + "\n".join(f"- {one}" for one in earlier)
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                    decision={"kind": Said.MAIL_LOOKED},
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _mail_runs(self, ctx: RequestContext, *, besides: set[str]) -> list[str]:
        since = self._clock.now() - K_MAIL_DAY
        async with self._uow as uow:
            runs = [
                run
                for run in await uow.workflow_runs.recent(ctx.tenant_id, limit=K_MAIL_RUNS)
                if run.mail
                and run.offer not in besides
                and answers_for(run, ctx.principal_id.value)
                and datetime.fromisoformat(run.started_at) >= since
            ]
            titles = {
                run.id: run.pinned.title
                if run.pinned is not None
                else (await uow.workflows.get(ctx.tenant_id, run.workflow_id)).title
                for run in runs
            }
        return [of_a_mail_run(run, titles[run.id]) for run in runs]

    async def _ask_which(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        said: str,
        choices: list[str | None],
        titles: list[str],
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                    decision={
                        "kind": "which_job",
                        "choices": [one for one in choices if one],
                        "titles": titles,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def matched(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        offer_id: str,
        trigger_id: str,
        named: str,
        skill_id: str = "",
        workflow_id: str = "",
        read: Sequence[str],
        missing: Sequence[str],
    ) -> None:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            if any(
                (message.decision or {}).get("offer_id") == offer_id for message in thread.messages
            ):
                return
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.SYSTEM,
                    text=f"A mail matched {named}",
                    said_at=self._clock.now(),
                    decision={
                        "kind": Said.MAIL_MATCH,
                        "offer_id": offer_id,
                        "trigger_id": trigger_id,
                        "skill_id": skill_id,
                        "workflow_id": workflow_id,
                        "skill_name": named,
                        "read": list(read),
                        "missing": list(missing),
                        "can_find": self._can_gather,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()

    async def _said_to_a_run(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, run_id: RunId
    ) -> Thread:
        async with self._uow as uow:
            thread = _opened_by_the_caller(ctx, await uow.threads.get(ctx.tenant_id, thread_id))
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id.value)
            if run is None or not answers_for(run, ctx.principal_id.value):
                raise Conflict("a note goes only to a run you started")
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=self._clock.now(),
                    decision={"kind": Said.NOTE, "run_id": run_id.value},
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def may_start(self, ctx: RequestContext, *, thread_id: ThreadId) -> None:
        async with self._uow as uow:
            _opened_by_the_caller(ctx, await uow.threads.get(ctx.tenant_id, thread_id))

    async def started(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        run_id: RunId,
        skill: Skill,
    ) -> Thread:
        async with self._uow as uow:
            thread = _opened_by_the_caller(ctx, await uow.threads.get(ctx.tenant_id, thread_id))
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=f"Running {skill.name}…",
                    said_at=self._clock.now(),
                    decision={
                        "kind": Said.RUN,
                        "matched_skill_id": skill.id.value,
                        "matched_version": skill.latest.version,
                        "run_id": run_id.value,
                        "matched_skill_name": skill.name,
                        "confident": True,
                        "runnable": True,
                        "missing_parameters": [],
                        "why": [],
                        "choices": [],
                        "items": [],
                        "note": "",
                        "proposal_sources": [],
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def performed(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        run: Run,
        skill_name: str,
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=_what_happened(run, skill_name),
                    said_at=self._clock.now(),
                    decision={
                        "kind": (Said.FAILURE if run.status is RunStatus.FAILED else Said.RESULT),
                        "next": ("open" if any(step.unreachable for step in run.steps) else "ask")
                        if run.status is RunStatus.FAILED
                        else "",
                        "matched_skill_id": run.skill_id.value,
                        "matched_version": run.skill_version,
                        "run_id": run.id.value,
                        "matched_skill_name": skill_name,
                        "confident": True,
                        "runnable": True,
                        "missing_parameters": [],
                        "why": [],
                        "choices": [],
                        "items": [],
                        "note": "",
                        "proposal_sources": [],
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _narrowed(self, ctx: RequestContext, resolution: Resolution) -> Asked | None:
        matched = resolution.matched
        if self._narrow is None or self._ask is None or matched is None:
            return None
        if writes(matched.version) or resolution.missing_parameters:
            return None

        key = matched.skill.objective_key
        narrowed = await self._narrow.for_utterance(
            ctx,
            utterance=resolution.utterance,
            version=matched.version,
            system=key.target_system,
            entity=key.entity_type,
            skill_id=matched.skill.id,
            unexplained=matched.unexplained,
            verb=resolution.verb,
        )
        if narrowed is None:
            return None
        if isinstance(narrowed, NeedToAsk):
            if narrowed.options:
                await self._write_down(ctx, narrowed)
            return Asked(None, "", narrowed.question)
        asked = await self._ask.execute(
            ctx, skill_id=matched.skill.id, url=narrowed.url, lead=narrowed.field
        )
        if asked.answer is None:
            logger.info("the narrowed read did not answer: %s", asked.detail)
            return None
        return replace(asked, detail=asked.detail or "; ".join(narrowed.because))

    async def _next_steps(
        self,
        ctx: RequestContext,
        resolution: Resolution,
        run: Run | None,
        narrowed: Asked | None,
    ) -> tuple[str, ...]:
        matched = resolution.matched
        if self._suggest is None or matched is None:
            return ()

        values: dict[str, tuple[str, ...]] = {}
        rows = 0
        if narrowed is not None and narrowed.answer is not None:
            values, rows = dict(narrowed.answer.distinct), narrowed.answer.rows
        elif run is not None:
            for step in reversed(run.steps):
                if step.found_values:
                    values, rows = dict(step.found_values), step.found_rows or 0
                    break
        if not values:
            return ()

        key = matched.skill.objective_key
        return await self._suggest.after(
            ctx, system=key.target_system, entity=key.entity_type, values=values, rows=rows
        )

    async def _write_down(self, ctx: RequestContext, asking: NeedToAsk) -> None:
        if self._questions is None:
            return
        await self._questions.raise_question(
            ctx,
            Ambiguity(
                system=asking.system,
                key=value_key(asking.system, asking.entity, asking.word),
                question=asking.question,
                options=asking.options,
                because=asking.because,
            ),
        )

    async def _look_it_up(
        self, ctx: RequestContext, text: str, resolution: Resolution
    ) -> Answers | None:
        if self._plan_lookups is None or self._run_lookups is None:
            return None
        if resolution.matched is not None or not is_a_question(text):
            return None
        return await LookItUp(self._plan_lookups, self._run_lookups).execute(
            ctx, text, within=K_WHILE_TALKING
        )

    async def _say_what_was_found(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, found: Answers
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=what_was_found(found),
                    said_at=now,
                    decision={
                        "kind": LOOKED,
                        "question": text,
                        "answers": [_seen(one, text) for one in found.looked],
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _answer_now(self, ctx: RequestContext, resolution: Resolution) -> Run | None:
        matched = resolution.matched
        if self._execute is None or matched is None:
            return None
        if resolution.missing_parameters or not resolution.runnable:
            return None
        if writes(matched.version):
            return None

        try:
            return await self._execute.execute(
                ctx,
                ExecutionRequest(
                    skill_id=matched.skill.id,
                    parameters=dict(resolution.items[0]) if resolution.items else {},
                    version=matched.version.version,
                ),
            )
        except (DomainError, TargetUnreachable) as refusal:
            logger.info("could not answer from the system: %s", refusal)
            return None


def _not_yet(
    pending: Pending, filled: Pending | None, text: str, offer: str
) -> tuple[str, dict[str, object]]:
    if filled is None:
        return (
            f"Dropped {pending.title}.",
            {
                "kind": Said.NOTE,
                "workflow_id": pending.workflow_id,
                "mail_thread": pending.mail_thread,
            },
        )
    if filled.without:
        return cannot_without(filled)
    refused = too_long_for(pending, text)
    return (
        (
            f"That is {len(text.strip())} characters and "
            f"{filled.asking_for} takes {refused}. "
            f"What should {filled.asking_for} be?"
            if refused is not None
            else turned_down(filled) + question(filled)
        ),
        {
            "kind": NEEDS,
            "workflow_id": filled.workflow_id,
            "title": filled.title,
            "values": dict(filled.values),
            "items": [dict(one) for one in filled.items],
            "missing": list(filled.missing),
            "watched": filled.watched,
            "limits": dict(filled.limits),
            "from_step": filled.from_step,
            "mail_thread": filled.mail_thread,
            "offer": offer,
            **asking_state(filled),
        },
    )


def _offer_of(messages: Sequence[Message], asked: MessageId) -> str:
    said = next((message for message in messages if message.id == asked), None)
    return _chained(said) if said is not None else asked.value


def _to_run(job: Pending, offer: str, can_find: bool) -> dict[str, object]:
    return {
        "kind": "job",
        "workflow_id": job.workflow_id,
        "title": job.title,
        "values": dict(job.values),
        "items": [dict(one) for one in job.items],
        "missing": list(job.missing),
        "limits": dict(job.limits),
        "from_step": job.from_step,
        "mail_thread": job.mail_thread,
        "can_find": can_find,
        "watched": job.watched,
        "offer": offer,
        **({"dropped": list(job.dropped)} if job.dropped else {}),
    }


def _why_it_failed(run: Run | None) -> str:
    if run is None or run.status is not RunStatus.FAILED:
        return ""
    for step in run.steps:
        if step.detail and "login page" in step.detail:
            return (
                " The connection is signed out — the system answered with its login page. "
                "Sign in once and ask again."
            )
        if step.detail and "no live value" in step.detail:
            return " The session is missing something the system signs its calls with."
    return ""


def _what_happened(run: Run, skill_name: str) -> str:
    sent = [step for step in run.steps if step.disposition is StepDisposition.PERFORMED]
    if run.status is RunStatus.FAILED:
        return (
            f"{skill_name} did not finish. {run.failure or 'One step did not do what it should.'}"
        )
    withheld = [step for step in run.steps if step.disposition is StepDisposition.WITHHELD]
    if withheld:
        return (
            f"{skill_name} ran at {run.stage} — {len(sent)} call"
            f"{'' if len(sent) == 1 else 's'} sent and "
            f"{len(withheld)} withheld for you to read before anything is written."
        )
    return f"{skill_name} ran. {len(sent)} call{'' if len(sent) == 1 else 's'} sent."


def _reply(resolution: Resolution) -> str:
    if resolution.matched is not None:
        skill = resolution.matched.skill.name
        version = resolution.matched.version
        if resolution.items and resolution.missing_parameters:
            wanted = ", ".join(resolution.missing_parameters)
            observed = _last_time(resolution, resolution.missing_parameters)
            return (
                f"{skill} does that. I still need {wanted}"
                f"{observed} — give me that and I will run it."
            )
        if resolution.items:
            n = len(resolution.items)
            return (
                f"{skill} does that. Here {'is' if n == 1 else 'are'} the {n} "
                f"{'item' if n == 1 else 'items'} I read from that — check them and "
                "say go."
            )
        if resolution.note:
            return f"{resolution.question or ''} {resolution.note}".strip()
        if resolution.question:
            return f"{resolution.question}"
        return (
            f"{skill} v{version.version} does that — {version.summary} "
            f"Say the word and I will run it."
        )
    if resolution.choices:
        return resolution.question or "More than one skill fits that."
    if resolution.proposal is not None:
        lines = "\n".join(f"· {step.what}" for step in resolution.proposal.steps[:5])
        return f"{resolution.question}\n\n{lines}\n\n{resolution.proposal.caveat}"
    return resolution.question or "I do not know how to do that yet."


def _last_time(resolution: Resolution, wanted: tuple[str, ...]) -> str:
    if resolution.matched is None:
        return ""
    seen = [
        f"{parameter.name} was {parameter.observed_values[0]} both times it was demonstrated"
        for parameter in resolution.matched.version.parameters
        if parameter.name in wanted and len(parameter.observed_values) == 1
    ]
    return f" ({'; '.join(seen)})" if seen else ""


def _what_it_found(asked: Asked, resolution: Resolution) -> str:
    answer = asked.answer
    if answer is None:  # pragma: no cover - guarded by the caller
        return "Nothing came back."
    subject = (
        resolution.matched.skill.objective_key.entity_type.replace("_", " ")
        if resolution.matched
        else "records"
    )
    return answer.sentence(subject)


def _derived(asked: Asked | None) -> dict[str, object]:
    if asked is None or asked.answer is None:
        return {}
    answer = asked.answer
    return {
        "derived": {
            "url": asked.url,
            "because": asked.detail,
            "rows": answer.rows,
            "total": answer.total,
            "columns": list(answer.columns),
            "found": [dict(row) for row in answer.sample[:200]],
        }
    }


def _decision(
    resolution: Resolution,
    run: Run | None = None,
    narrowed: Asked | None = None,
    suggestions: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "matched_skill_id": (resolution.matched.skill.id.value if resolution.matched else None),
        "matched_version": (resolution.matched.version.version if resolution.matched else None),
        "confident": resolution.confident,
        "runnable": resolution.runnable,
        "missing_parameters": list(resolution.missing_parameters),
        "why": list(resolution.why),
        "choices": [c.skill.id.value for c in resolution.choices],
        "items": [dict(item) for item in resolution.items],
        **_derived(narrowed),
        "suggestions": list(suggestions),
        "note": resolution.note,
        "proposal_sources": (list(resolution.proposal.sources) if resolution.proposal else []),
        "run_id": run.id.value if run else None,
        "matched_skill_name": resolution.matched.skill.name if resolution.matched else None,
        **({"pursuable": True} if resolution.pursuable else {}),
    }


def _last_asked(thread: Thread) -> str | None:
    for message in reversed(thread.messages):
        if message.speaker is Speaker.OPERATOR:
            return message.text
    return None


# The brain's tools that start a run, and what each is recorded as.
_STARTS = {"start_job": "start a job from chat", "undo_run": "take back a run"}


def _history(said: Sequence[Message]) -> list[str]:
    return [f"{one.speaker.value}: {one.text}" for one in said[-K_HISTORY:]]


def _open_question(said: Sequence[Message], answering: str | None) -> str:
    # Only a message that asks: a finished run's card is not a question to answer.
    asked = asked_under(said, answering)
    return asked.text if asked is not None and (asked.decision or {}).get("kind") in ASKS else ""


def _awaiting(thread: Thread) -> str | None:
    for message in reversed(thread.messages):
        if message.speaker is not Speaker.ASSISTANT or not message.decision:
            continue
        decision = message.decision
        if decision.get("missing_parameters"):
            matched = decision.get("matched_skill_id")
            return str(matched) if matched else None
        return None
    return None


LOOKED = Said.LOOKED.value


def _seen(looked: Looked, question: str = "") -> dict[str, object]:
    return as_seen(
        system=looked.lookup.system,
        target=looked.lookup.target,
        ok=looked.ok,
        detail=looked.detail,
        answer=looked.answer,
        read=looked.read,
        question=question,
    )


def _nothing_back(said: Sequence[Message]) -> str:
    for message in reversed(list(said)):
        decision = message.decision if isinstance(message.decision, dict) else None
        if not decision or decision.get("kind") != "mail_sent":
            continue
        if not decision.get("sent"):
            return ""
        to = str(decision.get("to") or "")
        return f"Nothing back from {to} yet. " if to else "Nothing back yet. "
    return "I am still waiting on this one. "


def _the_way_out(pending: Pending) -> str:
    asked = pending.asking_for
    return f' If you did mean that as {asked}, say "{asked}: ..." and I will take it.'


def _gathered(thread: Thread, skill_id: str | None) -> dict[str, str]:
    if skill_id is None:
        return {}
    values: dict[str, str] = {}
    for message in thread.messages:
        decision = message.decision or {}
        if str(decision.get("matched_skill_id") or "") != skill_id:
            continue
        items = decision.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                values.update({str(key): str(value) for key, value in item.items() if value})
    return values


def _chained(asked: Message) -> str:
    return str((asked.decision or {}).get("offer") or asked.id.value)


def _opened_by_the_caller(ctx: RequestContext, thread: Thread) -> Thread:
    if thread.opened_by != ctx.principal_id:
        raise Conflict("only the operator who opened this thread acts in it")
    return thread
