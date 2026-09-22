"""Say something to the system, and get back what it worked out.

The reply is never improvised. It is a rendering of a `Resolution`: the skill
that was matched and what it still needs, the choice between two that were too
close, or what the knowledge base knows about a task nobody has taught. The
prose exists so an operator can read it; the decision is stored beside it so an
auditor does not have to.

**Nothing is performed here.** A matched skill is offered, and starting it is a
separate request the operator makes — which is what makes their confirmation
the authorisation an assisted run records.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

from sro.application.chat.read_chat import ReadChat
from sro.application.chat.reading_an_answer import IsItAnAnswer
from sro.application.chat.understand import Understood
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
    let_go,
    offered_job,
    pending_job,
    question,
    said_yes,
    too_long_for,
)
from sro.domain.chat.is_it_an_answer import said_as_the_value
from sro.domain.chat.thread import Message, Said, Speaker, Thread, ThreadId
from sro.domain.execution.run import Run, RunId, RunStatus, StepDisposition
from sro.domain.lookup.asking import is_a_question
from sro.domain.shared.errors import DomainError
from sro.domain.skill.learned import demanded
from sro.domain.skill.skill import Skill

logger = logging.getLogger(__name__)


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


class _NotAsked:
    """Nobody has placed this sentence against the jobs yet.

    A sentinel rather than `None`, because `None` is already an answer on this
    path -- it is what `_placed_by_the_rig` returns for a sentence that names
    no job, which is exactly the case that must not be confused with "not
    looked at".
    """


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
        # Whether a sentence typed while a question stands is the answer to it.
        # Optional: a deployment without one takes every sentence, exactly as
        # this door did before the reading existed.
        self._answers = answers
        self._clock = clock
        self._ids = ids
        self._execute = execute
        self._narrow = narrow
        self._ask = ask
        self._questions = questions
        self._suggest = suggest
        # Whether a run of a mined job can go and find a value nobody typed.
        #
        # What the card asks for, and it is the difference between a person
        # being asked to type a code out of a mail they have open and a run
        # reading it themselves. Told to the panel rather than decided there:
        # the connector is a deployment's, and a browser cannot know whether
        # this one has a mailbox it may read.
        self._can_gather = can_gather
        # The door that owns a question.
        #
        # `/v1/ask` has always decided which of the two worlds a sentence
        # belongs to -- an instruction for the jobs, a question for the
        # lookups -- and this door never asked. So a question nothing was
        # taught for came back here as a PROPOSAL to open five screens and
        # work it out, seven seconds before the lookup door answered it
        # properly from an endpoint. Two answers on screen to one sentence,
        # and the wrong one first.
        #
        # Optional, like every other model-backed service here: a deployment
        # without one behaves exactly as this door did before.
        self._plan_lookups = plan_lookups
        self._run_lookups = run_lookups

    async def note(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> None:
        """Write something into the thread that nobody asked a question for.

        A pursuit finishes minutes after the request that started it, in a
        background task, and its progress lives only in this process. What it
        did has to end up somewhere an operator can read tomorrow.
        """
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
    ) -> Thread:
        if run_id is not None:
            return await self._said_to_a_run(ctx, thread_id=thread_id, text=text, run_id=run_id)
        # A question this conversation asked is answered by the next thing
        # said in it, before anything tries to read that sentence as a fresh
        # request.
        #
        # "GPP" placed against the jobs is a sentence about nothing. Against
        # the question that was actually asked -- *what should Customer Type
        # be?* -- it is the answer, and reading it any other way is how a
        # system asks somebody a question and then ignores what they say. It
        # also saves the model call: the reading that matters already happened
        # when the job was placed.
        async with self._uow as uow:
            said_before = (await uow.threads.get(ctx.tenant_id, thread_id)).messages
        waiting = await self._still_wanted(ctx, pending_job(said_before))
        if waiting is not None:
            # And only if it IS one. A question standing here used to take
            # whatever was typed next, which is right for `GU9` and wrong for
            # everything else somebody types while they wait -- and what they
            # type while waiting is usually about the waiting.
            #
            # Measured on the deployment 2026-09-18: the operator had sent the
            # answer by mail and typed `has reply arrived` to ask this system
            # whether it had landed. It was taken as the value, a run started a
            # millisecond later, and `HAS REPLY ARRIVED` went into a
            # four-character box in a live warehouse system.
            #
            # A sentence that is not an answer falls through to everything
            # below and is treated as what it is. The question is not consumed,
            # so it is still standing when they do answer it.
            answered_it, about = await self._is_it_an_answer(ctx, waiting, text)
            if answered_it is not None:
                return await self._answer_the_question(
                    ctx, thread_id=thread_id, text=answered_it, pending=waiting
                )
            # About the waiting, which is what a person who is waiting asks
            # about. Answered here and not handed on.
            #
            # `check now` went to the task resolver, which is a door for "what
            # work do you want done" -- so it planned one, and answered two
            # words about a mailbox with a wall of text about Check In and
            # Check Out screens nobody had mentioned. Seen on the deployment
            # 2026-09-18, 16:42.
            if about != "another_task":
                await self._also_said(ctx, thread_id=thread_id, text=text)
                return await self._ask_it_again(
                    ctx, thread_id=thread_id, pending=waiting, said_before=said_before
                )
            # And only where the jobs agree that it IS one.
            #
            # `another_task` is a model's reading of a sentence, and the
            # sentence that named this was `i wll type` -- the operator saying
            # they would type the value, in answer to a question asking for
            # it. Read as a request for different work, it went to the door
            # that proposes work: "Nobody has demonstrated that, so I would
            # work it out on the screen: i wll type", and five Configuration
            # menus nobody had mentioned. Measured on the deployment
            # 2026-09-21 at 17:10, in an operator's own conversation.
            #
            # The reading was wrong and no wording will make it always right.
            #
            # Refusing to carry on at all is not the answer either. Whether a
            # sentence is a request for different work cannot be decided from
            # the sentence -- "create an equipment type instead" places against
            # nothing on a tenant that has never demonstrated one, and it is
            # still a request. The door's own test says so: *somebody who says
            # "create an equipment type instead" has asked for work, and a door
            # that replied "I am still waiting on Customer Type" to that would
            # be the old swallowing with better manners*.
            #
            # What CAN be decided is whether there is anything to say. The harm
            # measured was not the carrying on; it was the PROPOSAL -- a door
            # with no taught skill, no lookup and no read still answering, out
            # of a plan it made from the screen. So the sentence is carried on
            # with (`standing`), and where all this door has for it is a plan
            # made up on the spot, it says nothing and the standing question is
            # what the operator sees.
            #
            # The placement is handed down, so this costs no extra model call
            # on the path that does turn out to be another task.
            placed = await self._placed_by_the_rig(ctx, text)
            # Said, answered, and then asked again.
            #
            # The asking again is not politeness. `pending_job` reads the LAST
            # thing the assistant decided, so an ordinary reply written under a
            # standing question buries it -- the sentence gets its answer and
            # the question is gone, which is the same swallowing by a longer
            # road. Repeating it is also what a person does: they answer what
            # they were asked, and then say what they are still waiting for.
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
            ctx, thread_id=thread_id, text=text, system=system, parameters=parameters
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
    ) -> Thread:
        """Everything this door does with a sentence that answers no question.

        The body of `execute` from the question check down, unchanged and
        named, so that a sentence which turned out NOT to be an answer can be
        handled the ordinary way rather than being dropped for not fitting a
        box it was never about.
        """
        async with self._uow as uow:
            said_before = (await uow.threads.get(ctx.tenant_id, thread_id)).messages
        # And a job this conversation has just offered, agreed to.
        #
        # Measured on the deployment, 2026-09-17 at 03:17. The assistant said
        # "Create a Customer Type does that -- say the word and I will run it",
        # the operator said "pls do", and the reply was "Nothing has been
        # taught for that": the sentence went to the resolver below, which
        # ranks this tenant's taught SKILLS and had never heard of it. Nothing
        # was holding on to what had just been offered.
        #
        # A system that asks for a word and then does not know the word is the
        # same fault as the boxes on the offer card: it asks, and then ignores
        # the answer.
        offered = offered_job(said_before)
        if offered is not None and said_yes(text):
            return await self._say_yes_to_it(ctx, thread_id=thread_id, text=text, offered=offered)
        # The rig's jobs first, and where they place the sentence, only them.
        #
        # An operator typed "lets create warehouse equipment type" at a browser
        # whose rig holds exactly that job, and was answered "Create a customer
        # type does that. I still need long_description." The resolver below
        # ranks the tenant's taught SKILLS -- seven of them, none about
        # equipment types -- so it answered with the nearest thing it had. The
        # right job was in the rig all along and this door never asked it.
        #
        # One model call and not two: the reading that answers here is the
        # reading the panel's offer is built from, rather than this door
        # spending one on the skills library and the browser spending another
        # on the jobs.
        # Asked here, unless the caller has already asked. A sentence typed
        # under a standing question is placed against the jobs BEFORE the
        # question is abandoned, and asking a second time would be a second
        # model call for an answer this already has.
        if isinstance(placed, _NotAsked):
            placed = await self._placed_by_the_rig(ctx, text)
        if placed is not None:
            return await self._say_the_job(ctx, thread_id=thread_id, text=text, placed=placed)
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)

        resolution = await self._resolver.execute(
            ctx,
            utterance=text,
            system=system,
            # Values already given for the skill under discussion. An operator
            # who answers one question at a time should not lose the first
            # answer when they give the second.
            parameters={**_gathered(thread, _awaiting(thread)), **(parameters or {})},
            # What was being talked about a moment ago. A conversation whose
            # every sentence is resolved alone is not a conversation.
            after=_last_asked(thread),
            pinned=_awaiting(thread),
        )

        # A question nothing was taught for belongs to the lookup door.
        #
        # The taught path below still comes first -- a skill that knows which
        # call answers a question is a better answer than a plan made from the
        # knowledge base. This is the case where there is no such skill, and
        # where this door used to answer with a PROPOSAL: "Nobody has
        # demonstrated reading that, so I will work it out on the screen",
        # followed by five screens to open.
        #
        # Measured on the deployment 2026-09-21. Asked "is there a customer
        # type called KKYT", three doors answered one sentence:
        #
        #   18:30:26  POST /v1/lookups            3601ms
        #   18:30:35  POST /v1/threads/../messages 7691ms  <- the screen walk
        #   18:30:43  POST /v1/ask                 6567ms  <- the answer
        #
        # The wrong one arrived first and read as final. The lookup planned
        # `call /data/WM/wm/customerTypes`, got 200, and found KKYT -- which
        # this door proposed to go and read off a screen instead.
        #
        # `is_a_question` is the same word rule `/v1/ask` decides by, with no
        # model, so the two doors cannot disagree about what a question is.
        looked = await self._look_it_up(ctx, text, resolution)
        if looked is not None:
            return await self._say_what_was_found(ctx, thread_id=thread_id, text=text, found=looked)

        # A question is answered from the system, now. The taught skill knows
        # which call answers it; what it saw when it was taught is a description
        # of that afternoon, and showing it as though it were current is how a
        # console tells somebody there are sixteen when there are twenty-three.
        #
        # Only reads, and only when nothing is missing. A write still waits for
        # the operator to say go -- that confirmation is what an assisted run
        # records as its authorisation, and it is not ours to assume.
        # The narrower question first, where the sentence asked one: replaying
        # a taught read that answers something wider is how "show me supplier
        # X" came back as every supplier there is.
        narrowed = await self._narrowed(ctx, resolution)
        # A question of our own stops the wider read too: answering something
        # nobody asked, because the thing they did ask could not be placed, is
        # the confident wrong answer wearing a table.
        run = None if narrowed else await self._answer_now(ctx, resolution)

        # A plan made up on the screen, under a question of ours that is still
        # standing. This is the one thing this door says that is worth not
        # saying: "Nobody has demonstrated that, so I would work it out on the
        # screen: i wll type", and five Configuration menus nobody mentioned.
        #
        # Only the PROPOSAL. A taught skill still answers, a lookup still
        # answers, and so does "Nothing has been taught for that" -- somebody
        # who asks for work this tenant has never demonstrated is owed that
        # sentence, not a second copy of the question they are already looking
        # at. What they are not owed is a plan this door invented because it
        # had nothing.
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
        """The standing question, minus anything the job no longer asks for.

        A question stands until it is answered or the job is dropped, and that
        is right -- it is what stops an ordinary reply burying it. What it
        missed is that the JOB can change underneath it. A field the job
        demanded on Monday may be one the page never asked for, learnt as a
        parameter only because two demonstrations happened to vary it, and
        since 2026-09-22 no longer demanded at all.

        Measured on the deployment that day. `Department takes 10 characters.
        What should it be?` was asked at 11:35 and was still being re-asked at
        13:50 -- two hours and four unrelated sentences later, under every one
        of them, for a field the job had stopped requiring in between. The
        operator asked for a new customer type, was offered one, and got the
        old question back under the offer. There is no answer that ends it
        except naming a value nobody needs, and no reason to.

        So the job's own declaration is read again here rather than trusted
        from when the question was written. It can only ever REMOVE names: a
        question is still a question about the job it named, and a field that
        has since become required is one the run will ask for itself.

        One read, and only where a question is standing. A thread with nothing
        waiting pays nothing.
        """
        if waiting is None or not waiting.workflow_id:
            return waiting
        async with self._uow as uow:
            job = await uow.workflows.get(ctx.tenant_id, waiting.workflow_id)
        # A job that declares nothing has said nothing, which is not the same
        # as saying nothing is required. A parameter is learnt from two doings
        # that varied a field, so a job done once declares none at all -- and
        # dropping its questions on that basis would silence every question a
        # young job ever asks.
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
        # Nothing left to ask. The question is over, and the sentence under it
        # is an ordinary sentence rather than an answer to something nobody
        # needs.
        return replace(waiting, missing=still) if still else None

    async def _question_stands(self, ctx: RequestContext, thread_id: ThreadId) -> bool:
        """Whether a question is standing NOW, rather than when this request
        began.

        `execute` reads the thread once, at the top, and everything after that
        is a model call: the reading, the placement, the resolver. Seconds. And
        the question this door would talk over is written by somebody else --
        `RunWorkflow._ask_for_values` (`workflow_runs.py:589`), from a task the
        start-run route spawned and never awaited (`routers/workflow_runs.py:
        139`), after a whole live browser run has tried and failed to find the
        values. Two independent transactions on one thread, no lock between
        them.

        Measured on the deployment 2026-09-22 at 01:06. The operator asked for
        a customer type, the run went to look in their mail, and they typed
        `i will type` while it was looking. This door had read the thread
        before the run's question was committed, so `pending_job` saw a job
        offer rather than a question, `standing` was false, and the guard below
        never fired: *"Nobody has demonstrated that, so I would work it out on
        the screen: i will type"*, and five Configuration menus. The question
        landed a moment later and was buried under them -- which is why the
        stored thread has the question at 20 and the plan at 22.

        So the freshest possible read, at the last possible moment, and only on
        the path that is about to say the one thing worth not saying. It does
        not close the window -- an operator who types before the run has asked
        anything still meets a thread with no question in it -- and that
        remainder is the run's own flight, not this read. What it does close is
        every case where the question was already written by the time this door
        decided, which is the case that was measured.
        """
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
        return pending_job(thread.messages) is not None

    async def _also_said(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> Thread:
        """Write down what they said, without acting on it.

        The sentence is theirs and it was said: a conversation that answers a
        person without showing what they asked reads, a minute later, as the
        system talking to itself.
        """
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
        """Put the standing question back, under whatever was just said.

        The same decision it was asked with, so the state rides along intact --
        what is established, what is still missing, where the run had got to.
        A question re-asked with a thinner decision than the one it replaces is
        a question that loses an answer somebody already gave.
        """
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
        """The value to take, or None where that sentence was not an answer.

        Never None where nothing could read it. A deployment with no model, a
        reading that raised, a cap spent -- all of them behave as this door
        behaved before the reading existed, because a panel that quietly stops
        accepting answers when a model is unreachable is worse than one that
        takes too many.

        `let_go` first and without asking anybody: "no" and "never mind" end
        the question, and a reading asked whether "no" answers "what should
        Customer Type be" has been given a question with no good answer.
        """
        if let_go(text) or self._answers is None:
            return text, ""
        # Named by the person themselves, and nothing needs to be read.
        #
        # This is the way out of the loop. The reading is told to refuse when
        # it is unsure, which is the right default and leaves an operator who
        # typed a real value with no move except typing it again -- so the
        # re-ask below tells them this form exists, and this takes it.
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
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, pending: Pending
    ) -> Thread:
        """Take that sentence as the value it was asked for, and go on.

        Three ends, and the whole state of it lives on the decision each one
        writes -- not in a session, not on a row. An operator answering two
        questions over five minutes does not depend on a process staying up,
        and a second browser reading the thread sees the same thing.

        **Called off.** "No", "never mind": said whole, never by substring, so
        a description reading "leave it in receiving" is a description.

        **One down, more to go.** The answer goes in, the next question comes
        out, and the decision carries what is established so far.

        **The last one.** No more questions: the job is said back as a `job`
        decision with nothing missing and `resume`, which is the panel's cue to
        start it without asking again. They already said yes; asking twice for
        the same permission is how a system teaches somebody to stop reading
        what it asks.
        """
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
            said: str
            decision: dict[str, object]
            if let_go(text):
                said, decision = (
                    f"Dropped {pending.title}.",
                    {"kind": Said.NOTE, "workflow_id": pending.workflow_id},
                )
            else:
                filled = answered(pending, text)
                # An answer the box will not hold leaves the question standing,
                # and saying so is the whole difference between a loop somebody
                # can get out of and one they cannot. Silently re-asking the
                # same question reads as a system that ignored them.
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
                            # Where the run that asked had got to. Without it
                            # the answer starts the job from the beginning and
                            # re-walks every step the first run performed, to
                            # arrive back at the box it stopped in front of.
                            "from_step": filled.from_step,
                            # So the run this answer starts answers to the same
                            # mail a run the card started would have.
                            "mail_thread": filled.mail_thread,
                            "can_find": self._can_gather,
                            # They already pressed yes. This is the same press
                            # arriving late, not a second one to ask for.
                            "resume": True,
                            "watched": filled.watched,
                        },
                    )
                    if filled.ready
                    else (
                        (
                            f"That is {len(text.strip())} characters and "
                            f"{filled.asking_for} takes {refused}. "
                            f"What should {filled.asking_for} be?"
                            if refused is not None
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
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, offered: Pending
    ) -> Thread:
        """Start the job that was just offered, or ask for what it still needs.

        Two ends, and which one is decided by whether anything can go and look.
        A deployment that can read the operator's mail starts the job and lets
        the run find the rest -- that is what the card's own Yes does, and a
        conversation that demanded values the card would not is two answers to
        one question. A deployment that cannot asks here, one value at a time,
        and `_answer_the_question` takes it from there.
        """
        ready = offered.ready or self._can_gather
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
            }
            if ready:
                # The press, arriving as a sentence. `resume` is what tells the
                # panel this is the yes and not another offer to answer.
                decision["resume"] = True
            else:
                decision["kind"] = NEEDS
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=(f"Running {offered.title} now." if ready else question(offered)),
                    said_at=self._clock.now(),
                    decision=decision,
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _placed_by_the_rig(self, ctx: RequestContext, text: str) -> Understood | None:
        """Which mined job this sentence is about, or None to ask the skills.

        None on every refusal as well as on a sentence the rig cannot place:
        no model configured, the day's cap spent, a door that raised. The
        conversation still happens -- it happens the way it did before this
        existed, which is the behaviour the console has always had.
        """
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
        """The rig's answer, in the thread, with what a press would need."""
        async with self._uow as uow:
            known = {one.id: one for one in await uow.workflows.known(ctx.tenant_id)}
            title = known[placed.workflow_id].title if placed.workflow_id in known else "That job"
            things = len(placed.items)
            # Not sure which job: ask, rather than start one.
            #
            # The reading is still the best one it had, and it is offered
            # first -- but as a question with the others beside it, and with no
            # `workflow_id` for a press to act on. A guess that creates one
            # wrong record is a nuisance; the same guess against a list of
            # twenty is twenty wrong records in a warehouse, and the cost of
            # asking is one sentence.
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
            if placed.missing and self._can_gather:
                # The run goes and looks. Said as what will happen rather than
                # as a demand, because the demand was the old behaviour and it
                # put a person in front of four boxes -- two of them the body
                # keys a form posts, which nobody has ever typed -- for values
                # sitting in the mail that asked for the job.
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
                    # The structured half, which is what a press is built from:
                    # the browser makes its offer out of this rather than
                    # spending a second reading of the same sentence.
                    decision={
                        "kind": "job",
                        "workflow_id": placed.workflow_id,
                        "title": title,
                        "values": dict(placed.values),
                        "items": [dict(one) for one in placed.items],
                        "missing": list(placed.missing),
                        # Whether the missing ones are a demand or a plan. The
                        # panel draws its boxes off this: required where
                        # nothing can go and look, optional where something
                        # can, and a blank that reaches the door is refused as
                        # a typed blank either way.
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
        """A question with the jobs it was choosing between, and no press.

        `kind: "which_job"` and deliberately not `"job"`: the browser builds an
        offer out of a job decision, and a decision it cannot act on must not
        look like one it can.
        """
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
                        # The names, because the question is asked of a person:
                        # a panel drawing two buttons reading `wfl_c79d02bb`
                        # asks nobody anything.
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
        """A watched mailbox recognised a task. Said once, by name.

        A skill or a mined job: `named` is what the person reads and the two
        ids say which kind it was, because the press that follows goes to a
        different door for each. One method rather than two -- the sentence,
        the once-per-offer rule and the "names, never values" rule are the same
        for both, and a second copy of them is two that drift.

        The operator has to see this somewhere that survives the panel closing,
        which is the thread. What must not follow it there are the values: they
        were read out of somebody's mail, and `ValueAt` exists so they stay in
        the browser that read them. So the message carries which names were
        read and not what they said. The browser still holds the values, and
        the press that starts a run carries them then.

        Once per offer. A browser reports a match per frame it sees the mail in,
        and a conversation that says the same sentence four times is one nobody
        reads. Recognised by the offer id the browser minted -- absent from an
        older extension, which is why nothing is written without one: there
        would be no way to tell the second report from the first.
        """
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
                        # Where nothing can go and look, this is what the card
                        # says it cannot run without. Where something can, the
                        # names are still said -- a person reading the thread
                        # should know which values the mail did not carry --
                        # and `can_find` is what decides whether the button is
                        # a demand or a plan.
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
        """Something said to a run that is happening, rather than a request.

        Not `note` above, which is this class's other way of writing into a
        thread: that one is the system reporting a pursuit that finished in the
        background, and this one is the operator talking. Two methods of one
        name meaning opposite halves of an exchange is a trap for whoever reads
        them next.

        Kept and not resolved. An operator watching a run who types "use the
        north yard address" is talking about the thing in front of them; putting
        that sentence through intent matching finds some other skill and offers
        to run it, which is the opposite of what they meant.

        Nothing acts on it yet. It is recorded against the run so it is in the
        transcript beside the step it arrived during, and so the surface can say
        honestly that it was heard -- what reads it is the planner, when there
        is one. A note that silently changed a run would be worse than one that
        does nothing: the values a run uses are changed by `ReviseRun`, where
        the change is checked against the names the skill declares.
        """
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
        """Put a run into the conversation the moment it starts.

        Before, the message was written when the run finished, so a task that
        takes twelve seconds left the operator with a spinner and a card that
        forgot what it was doing. The message is the anchor: the console
        streams the steps into it as they land, and it is already in the
        transcript if the browser is closed halfway.
        """
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
        """Write a run the operator started into the conversation that asked for it.

        Until now a run started from a card lived in the console's memory: it
        survived nothing -- a re-render put the empty form back, and a reload
        lost the fact that anything had happened at all. A run belongs in the
        transcript for the same reason every other decision does. Somebody
        reading this thread tomorrow needs to see that a supplier was created,
        by whom, and what came back.
        """
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
                        # The one thing that would help, for a surface that
                        # shows a failure as a sentence and a single button.
                        # A step nothing could reach is a page to open; every
                        # other failure is somebody's to look at.
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
        """The question that was actually asked, where the taught skill answers
        a wider one.

        "Show me supplier TESTSUPPLIERSRO" matched the read that lists every
        supplier, and replaying it returned all two hundred and thirty-nine --
        the one word that said which supplier was dropped on the floor. Here
        the field dictionary says what that value is called, the taught call
        proves the filter dialect, and the request is composed from both.
        """
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
            # The verb is what they want done, not a value to filter by:
            # "count the addresses" asked which field the word "count" names,
            # because two fields are called Count something.
            verb=resolution.verb,
        )
        if narrowed is None:
            return None
        if isinstance(narrowed, NeedToAsk):
            # Only a real choice becomes a question. A statement that this read
            # cannot answer the sentence is not something to ask anybody.
            if narrowed.options:
                await self._write_down(ctx, narrowed)
            return Asked(None, "", narrowed.question)
        asked = await self._ask.execute(
            ctx, skill_id=matched.skill.id, url=narrowed.url, lead=narrowed.field
        )
        if asked.answer is None:
            # The narrowing was right and the request did not work -- an
            # expired session, an endpoint that answered nothing. Falling back
            # to the taught read answers a wider question, but answering
            # nothing at all because a composed request failed is worse.
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
        """What can be asked next, from what this answer actually contains."""
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
        """Keep the question, so answering it once teaches it for everybody.

        The next person to ask about "parcel" gets a narrowed read rather than
        the same question, because what an operator says a word means is
        knowledge like anything else here.
        """
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
        """The lookup door's answer to this question, or None if it is not one.

        None on every path that is not "a question with no skill behind it":
        a sentence that asks for work, a question a taught skill matched, a
        deployment with no lookup services, a plan that came back unready.
        Each of those falls through to what this door did before, which is
        still the right answer for them.
        """
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
            # Nothing here knows how to look it up, which is the case the
            # proposal below is genuinely for: it says what the knowledge base
            # has and offers to work the screen out once.
            return None
        # `allow_focus` false, always. A question is not a reason to take the
        # screen somebody is working on -- that is the refusal
        # (`focus_not_permitted`) this whole path exists to stop meeting.
        #
        # And `K_WHILE_TALKING`, not the lookup door's own budget. A reply in a
        # panel is a turn in a conversation, and a turn that takes a minute has
        # stopped being one: measured on the deployment 2026-09-21, request
        # `req_10d3ff9b`, the browser's socket dropped twice inside one
        # request, a command waited out the full 45 seconds, and the reply took
        # 67459ms. Routing the conversation through this door is what made a
        # thread reply wait on a browser at all; this is what stops it waiting
        # on one that is not answering.
        return await self._run_lookups.execute(
            ctx, plan=planned.plan, allow_focus=False, within=K_WHILE_TALKING
        )

    async def _say_what_was_found(
        self, ctx: RequestContext, *, thread_id: ThreadId, text: str, found: Answers
    ) -> Thread:
        """The answer, in the thread, carried as structure rather than prose.

        The panel already has the renderer: `result.js` reads a body, counts
        the records and draws the first few in a table. What it could not do
        was reach one -- a lookup's answer arrived only through `/v1/ask`, into
        a card beside the conversation, while the conversation itself carried
        the screen walk. So the decision carries the same shape that card is
        built from and the thread draws it the same way.
        """
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
        """Run a read the moment it is asked for, and answer with what came back."""
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
            # A refused read is worth saying out loud, and worth saying in the
            # reply rather than as an empty answer: the breaker being open is a
            # fact about the system, not an absence of transport modes.
            logger.info("could not answer from the system: %s", refusal)
            return None


def _why_it_failed(run: Run | None) -> str:
    """Say what actually went wrong, in the words of the thing that went wrong.

    "1 step did not satisfy their post-conditions" is true of a skill that has
    drifted, a system that is down, and a session that has expired, and those
    want three different people to do three different things. The step already
    knows which; it was just not being read.
    """
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
    """One line about a run, in the words of what it did."""
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
    """What to say. Every branch says what happens next, because a reply that
    only reports a state leaves the operator to guess at the next move."""
    if resolution.matched is not None:
        skill = resolution.matched.skill.name
        version = resolution.matched.version
        if resolution.items and resolution.missing_parameters:
            # Values were read, but not all of them. Telling somebody to "say
            # go" when the run cannot start is how a system trains people to
            # ignore what it says.
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
    """What the demonstrations used, where that is all anybody has to go on.

    A parameter that exists because an operator asked to be prompted for it was
    a constant a moment ago, and saying what it was is the difference between a
    question somebody can answer and one they have to go and look up.
    """
    if resolution.matched is None:
        return ""
    seen = [
        f"{parameter.name} was {parameter.observed_values[0]} both times it was demonstrated"
        for parameter in resolution.matched.version.parameters
        if parameter.name in wanted and len(parameter.observed_values) == 1
    ]
    return f" ({'; '.join(seen)})" if seen else ""


def _what_it_found(asked: Asked, resolution: Resolution) -> str:
    """What a composed read found, in the words of the question."""
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
    """A composed read, as the console renders any other answer.

    Carried with where it came from: a request this system wrote is only
    trustworthy if the operator can see what it was built out of.
    """
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
    """The structured half of the reply, kept for the audit trail."""
    return {
        "matched_skill_id": (resolution.matched.skill.id.value if resolution.matched else None),
        "matched_version": (resolution.matched.version.version if resolution.matched else None),
        "confident": resolution.confident,
        "runnable": resolution.runnable,
        "missing_parameters": list(resolution.missing_parameters),
        "why": list(resolution.why),
        "choices": [c.skill.id.value for c in resolution.choices],
        # The table the operator confirms. Rendered rather than acted on: their
        # confirmation is what an assisted run records as its authorisation.
        "items": [dict(item) for item in resolution.items],
        **_derived(narrowed),
        # Earned from this answer's own columns and the skills taught for this
        # entity. Never a fixed list: the console used to offer "which X are
        # used for parcel" under every result in the system.
        "suggestions": list(suggestions),
        "note": resolution.note,
        "proposal_sources": (list(resolution.proposal.sources) if resolution.proposal else []),
        # The answer, from the system, at the moment it was asked.
        "run_id": run.id.value if run else None,
        # The name, not only the id: a sidebar reading "ran skl_a6f7b33c" tells
        # nobody anything.
        "matched_skill_name": resolution.matched.skill.name if resolution.matched else None,
    }


def _last_asked(thread: Thread) -> str | None:
    """The operator's previous sentence, which is where a follow-up's subject is.

    Theirs rather than the assistant's: the reply is full of words the system
    chose, and letting those steer the next match would have the console
    talking to itself.
    """
    for message in reversed(thread.messages):
        if message.speaker is Speaker.OPERATOR:
            return message.text
    return None


def _awaiting(thread: Thread) -> str | None:
    """The skill the last reply asked for values for, if it is still waiting."""
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
"""The decision a lookup's answer rides on into the conversation.

Its own kind, and not `note`: the panel draws it with `result()`, which counts
the records and puts the first few in a table. A kind nobody recognises is a
sentence, and a sentence about fifty records is the raw-JSON preview this
replaced."""


K_RAN_OUT = ("timeout", "timed out", "deadline")
"""What the channel says when nobody answered in time. The extension's own
words, matched here rather than translated -- `unreachable` is a browser that
said no and this is one that said nothing, and they want different sentences."""


def _ran_out(detail: str) -> bool:
    said = (detail or "").lower()
    return any(word in said for word in K_RAN_OUT)


def _seen(looked: Looked, question: str = "") -> dict[str, object]:
    """One answer, in the shape every surface draws it from. See
    `application.lookup.answer.as_seen` -- the trimming is there so the card, the
    conversation and a model asked to read it all get the same answer."""
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
    """The sentence above the table, for a surface that draws no table.

    Deliberately thin. What the answer SAYS is in the records, and a sentence
    claiming to summarise them would be this system inventing a number: the
    table is the answer and this is its label.
    """
    answered = [one for one in found.looked if one.ok]
    if not answered:
        why = next((one.detail for one in found.looked if one.detail), "")
        # Name the browser where the browser is what did not answer. "I could
        # not read that. timeout" is a sentence about this system's plumbing;
        # the person reading it can see their own browser and can do something
        # about it.
        if any(_ran_out(one.detail) for one in found.looked):
            return (
                "I could not reach your browser in time, so I have not read that yet."
                " Ask again and I will try once more."
            )
        return f"I could not read that. {why}".strip()
    # The reader's own sentence, where it read records.
    #
    # `Answer.sentence` is deterministic -- counted and named from the payload,
    # never summarised by a model, because "16" has to be 16 -- and it is the
    # line somebody asking a question wanted instead of a table. "Read from
    # /data/WM/wm/customerTypes" was this door describing its own plumbing.
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
    """ "Nothing back from them yet" -- where a mail is what is being waited on.

    Read off the thread rather than guessed: the last mail this conversation
    sent, and the fact that its answer has not arrived. The second half needs
    no checking. A reply that had been read would have filled the value, and
    this sentence is only ever written while the question is still standing.

    Empty for a question nobody was mailed about, which is most of them: a run
    that came up short in front of a person asks the person.
    """
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
    """How to be taken at your word, said where it is needed.

    Every re-ask happens because a reading refused to take a sentence as the
    value, and that reading is told to refuse when it is unsure -- which is
    the right default and leaves somebody who typed a real value with no move
    except typing it again and being refused again. `question` already names
    that loop as the thing this design must not be, for the length case. This
    is the same exit for the reading case: `said_as_the_value` takes a value
    the person named themselves without asking anybody, and this is the only
    place they are ever told so.
    """
    asked = pending.asking_for
    return f' If you did mean that as {asked}, say "{asked}: ..." and I will take it.'


def _gathered(thread: Thread, skill_id: str | None) -> dict[str, str]:
    """Every value established so far **for this skill**.

    Read back off the decisions rather than held in memory: the thread is what
    survives a restart, and an operator answering three questions over five
    minutes should not depend on a process staying up.

    Filtered by skill, which the docstring always claimed and the code never
    did: it merged the values from every decision in the thread, so a thread
    where somebody asked about suppliers and then went on to create a client
    carried the supplier's values into the client's parameters. Values arriving
    from somewhere the operator never typed them is the worst possible way for a
    write to be wrong -- it looks answered.

    Nothing is gathered when nothing is being waited on. A fresh sentence brings
    its own values; the thread's older ones belong to whatever they were for.
    """
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
