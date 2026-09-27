from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

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
from sro.application.lookup.answer import as_seen, subject_of
from sro.application.lookup.plan_lookups import PlanLookups
from sro.application.lookup.run_lookups import (
    K_WHILE_TALKING,
    Answers,
    Looked,
    RunLookups,
)
from sro.application.ports.http import TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.asking import (
    NEEDS,
    Pending,
    answered,
    asked_under,
    let_go,
    of_the_offer,
    offered_job,
    pending_job,
    question,
    said_yes,
    too_long_for,
)
from sro.domain.chat.is_it_an_answer import said_as_the_value
from sro.domain.chat.request import K_A_LOGIN
from sro.domain.chat.standing import last_run, of_the_run, stands
from sro.domain.chat.thread import Message, MessageId, Said, Speaker, Thread, ThreadId
from sro.domain.execution.run import Run, RunId, RunStatus, StepDisposition
from sro.domain.lookup.asking import is_a_question
from sro.domain.shared.errors import DomainError
from sro.domain.skill.learned import demanded
from sro.domain.skill.skill import Skill

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


NOT_ASKED = _NotAsked()


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
    ) -> None:
        self._uow = uow
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

    async def note(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> None:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
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
        if before.opened_by != ctx.principal_id and (
            answering is not None
            or pending_job(said_before) is not None
            or offered_job(said_before) is not None
        ):
            return await self._only_said(ctx, thread_id=thread_id, text=text, said=K_NOT_YOURS)
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
                    ctx, thread_id=thread_id, pending=waiting, said_before=said_before
                )
            placed = await self._placed_by_the_rig(ctx, text)
            await self._carry_on(
                ctx,
                thread_id=thread_id,
                text=text,
                system=system,
                parameters=parameters,
                placed=placed,
                standing=True,
            )
            return await self._ask_it_again(
                ctx, thread_id=thread_id, pending=waiting, said_before=said_before
            )
        return await self._carry_on(
            ctx,
            thread_id=thread_id,
            text=text,
            system=system,
            parameters=parameters,
            answering=answering,
        )

    async def _only_said(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, said: str = K_CLOSED
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            self._told(thread, text, said)
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    def _told(self, thread: Thread, text: str, said: str) -> None:
        for speaker, words in ((Speaker.OPERATOR, text), (Speaker.ASSISTANT, said)):
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=speaker,
                    text=words,
                    said_at=self._clock.now(),
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

    async def _still_wanted(self, ctx: RequestContext, waiting: Pending | None) -> Pending | None:
        if waiting is None or not waiting.workflow_id:
            return waiting
        async with self._uow as uow:
            job = await uow.workflows.get(ctx.tenant_id, waiting.workflow_id)
        if job is None or not job.parameters:
            return waiting
        wanted = {
            str(name)
            for one in job.parameters
            if isinstance(one, dict)
            and isinstance(name := one.get("name"), str)
            and name
            and demanded(one)
        }
        still = tuple(name for name in waiting.missing if name in wanted)
        if still == waiting.missing:
            return waiting
        return replace(waiting, missing=still) if still else None

    async def _what_stands(self, ctx: RequestContext, thread: Thread) -> str | None:
        now = self._clock.now()
        if (run_id := last_run(thread.messages)) is not None:
            async with self._uow as uow:
                run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
                seen = run is not None and ctx.principal_id.value in (
                    thread.opened_by.value,
                    run.started_by,
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
        named = said_as_the_value(pending, text)
        if named is not None:
            return named, ""
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
            if still is None or still.id != asked:
                self._told(thread, text, K_CLOSED)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            said: str
            decision: dict[str, object]
            if let_go(text):
                said, decision = (
                    f"Dropped {pending.title}.",
                    {
                        "kind": Said.NOTE,
                        "workflow_id": pending.workflow_id,
                        "mail_thread": pending.mail_thread,
                    },
                )
            else:
                filled = answered(pending, text, logins)
                refused = too_long_for(pending, text)
                said, decision = (
                    (
                        f"Running {filled.title} now.",
                        {
                            "kind": "job",
                            "workflow_id": filled.workflow_id,
                            "title": filled.title,
                            "values": dict(filled.values),
                            "items": [dict(one) for one in filled.items],
                            "missing": [],
                            "limits": dict(filled.limits),
                            "from_step": filled.from_step,
                            "mail_thread": filled.mail_thread,
                            "can_find": self._can_gather,
                            "resume": True,
                            "watched": filled.watched,
                            "offer": asked.value,
                        },
                    )
                    if filled.ready
                    else (
                        (
                            f"That is {len(text.strip())} characters and "
                            f"{filled.asking_for} takes {refused}. "
                            f"What should {filled.asking_for} be?"
                            if refused is not None
                            else f"That is {K_A_LOGIN}. {question(filled)}"
                            if filled == pending
                            else question(filled)
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
                        },
                    )
                )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                    decision=decision,
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

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
            if still is None or still.id != asked:
                self._told(thread, text, K_CLOSED)
                await uow.threads.save(thread)
                await uow.commit()
                return thread
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=self._clock.now(),
                )
            )
            decision: dict[str, object] = {
                "kind": "job",
                "workflow_id": offered.workflow_id,
                "title": offered.title,
                "values": dict(offered.values),
                "items": [dict(one) for one in offered.items],
                "missing": [] if ready else list(offered.missing),
                "limits": dict(offered.limits),
                "from_step": offered.from_step,
                "mail_thread": offered.mail_thread,
                "can_find": self._can_gather,
                "watched": offered.watched,
                "offer": str((still.decision or {}).get("offer") or asked.value),
            }
            said = f"Running {offered.title} now." if ready else question(offered)
            if let_go(text):
                said = f"Left {offered.title}."
                decision = {
                    "kind": Said.NOTE,
                    "workflow_id": offered.workflow_id,
                    "mail_thread": offered.mail_thread,
                }
            elif ready:
                decision["resume"] = True
            else:
                decision["kind"] = NEEDS
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=said,
                    said_at=self._clock.now(),
                    decision=decision,
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _placed_by_the_rig(self, ctx: RequestContext, text: str) -> Understood | None:
        if self._reads_jobs is None:
            return None
        try:
            placed = await self._reads_jobs.execute(ctx, utterance=text)
        except Exception:
            logger.info("the rig could not place %r; asking the skills instead", text[:40])
            return None
        return placed if placed.workflow_id else None

    async def _say_the_job(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, placed: Understood
    ) -> Thread:
        async with self._uow as uow:
            known = {one.id: one for one in await uow.workflows.known(ctx.tenant_id)}
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
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
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

    async def started(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        run_id: RunId,
        skill: Skill,
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
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
        try:
            planned = await self._plan_lookups.execute(ctx, question=text)
        except DomainError as refusal:
            logger.info("%s: the lookup could not be planned: %s", ctx.tenant_id.value, refusal)
            return None
        if not planned.plan.ready:
            return None
        return await self._run_lookups.execute(ctx, plan=planned.plan, within=K_WHILE_TALKING)

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
                    text=_what_was_found(found),
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


LOOKED = "looked"


K_RAN_OUT = ("timeout", "timed out", "deadline")


def _ran_out(detail: str) -> bool:
    said = (detail or "").lower()
    return any(word in said for word in K_RAN_OUT)


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


def _what_was_found(found: Answers) -> str:
    answered = [one for one in found.looked if one.ok]
    if not answered:
        why = next((one.detail for one in found.looked if one.detail), "")
        if any(_ran_out(one.detail) for one in found.looked):
            return "I could not read that in time. Ask again and I will try once more."
        return f"I could not read that. {why}".strip()
    said = [
        one.read.sentence(subject_of(one.lookup.target) or "record")
        for one in answered
        if one.read is not None
    ]
    if said:
        return " ".join(said)
    where = ", ".join(sorted({one.lookup.target for one in answered}))
    return f"Read from {where}."


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
