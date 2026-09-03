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

from sro.application.context import RequestContext
from sro.application.execution.derived_read import Asked, AskTheSystem
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.intent.match import writes
from sro.application.intent.narrow import NarrowARead, NeedToAsk, value_key
from sro.application.intent.next_steps import SuggestNext
from sro.application.intent.resolve import Resolution, ResolveIntent
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.http import TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Said, Speaker, Thread, ThreadId
from sro.domain.execution.run import Run, RunId, RunStatus, StepDisposition
from sro.domain.shared.errors import DomainError
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
    ) -> None:
        self._uow = uow
        self._resolver = resolver
        self._clock = clock
        self._ids = ids
        self._execute = execute
        self._narrow = narrow
        self._ask = ask
        self._questions = questions
        self._suggest = suggest

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

    async def matched(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        offer_id: str,
        trigger_id: str,
        skill: Skill,
        read: Sequence[str],
        missing: Sequence[str],
    ) -> None:
        """A watched mailbox recognised a task. Said once, by name.

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
                    text=f"A mail matched {skill.name}",
                    said_at=self._clock.now(),
                    decision={
                        "kind": Said.MAIL_MATCH,
                        "offer_id": offer_id,
                        "trigger_id": trigger_id,
                        "skill_id": skill.id.value,
                        "skill_name": skill.name,
                        "read": list(read),
                        "missing": list(missing),
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
