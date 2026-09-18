"""A mail that asks for a job, recognised by what it means.

The rung this replaces is a substring. A watch is `subject contains "Short
ship"` plus locators somebody marked by hand, and it will miss "please set up a
new client category" for as long as it exists -- not because the rule is badly
written, but because a rule made of words the operator typed once cannot be a
statement about meaning.

So the mail goes through the door that already decides what a piece of text
means: `understand`, which reads it against every job this tenant holds, with
each job's parameters, the values those have taken, and -- since
`domain.chat.asked_by` -- the mails the operator acted on before doing it.
That last part is why this can be a fair reading rather than a model guessing
from titles: a request rarely uses a job's words, and what a request for this
job looks like is a thing the demonstrations recorded.

**It offers, and it never runs.** A fuzzy reading that started a run would be
an autonomous system nobody opted into, on the strength of a model's opinion
about somebody's mail. What comes back is an offer the browser turns into the
card it already draws, with its existing press and the approval ladder
underneath, and a person still taps.

**And it writes nothing into the conversation.** The card is browser-held and
transient, which is the rule the panel already keeps: an offer ends when it is
pressed, when the operator does the job themselves, when they dismiss it, or
when their day does -- and the thread is the record of what was DECIDED. A
conversation that filled up with "a mail asks for X" would be a surface keeping
history of questions instead of answers, which is exactly the stillness the
panel is being split to end.

**Silence beats a wrong card.** A reading that is not `sure` writes nothing. A
mail nobody was asking about is the common case in any mailbox: a card per
delivery notice is a panel nobody reads by the fourth, and the cost of missing
one is that the operator types a sentence, which is what they do today anyway.

**Once per message, ever.** A look every few minutes over the same inbox would
otherwise offer the same mail forty times. The claim ledger `tool_calls` keeps
is exactly this shape -- a key, claimed once, with a window -- so it is what
this uses rather than a table of its own.

Read as the operator, through their own connector grant. `ToolCaller` takes the
principal and this passes it down: a look that reached another operator's
mailbox would be the boundary undone one layer up.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.understand import understand
from sro.application.context import RequestContext
from sro.application.execution.declared import declared_limits, names_of, screen_for
from sro.application.execution.gather import GatherContext
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.asking import NEEDS, Pending, pending_job, question
from sro.domain.chat.thread import Said, Speaker
from sro.domain.execution.learned_step import limits_for, too_long
from sro.domain.execution.waiting import read_wait, still_waiting
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Workflow

SERVER = "gmail"
"""The connector this looks in, named rather than every connector a deployment
holds. `gather.SERVER` says the whole of why."""

K_LOOK = 8
"""How many of the newest messages one look reads.

Bounded because a look somebody is waiting on has to end, and because eight
cards at once is a panel nobody reads past the third -- not because of what the
readings cost. Eight covers a morning's arrivals between looks.
"""

K_THREAD = 8000
"""How much of one conversation is read back. Long enough for a thread of a
dozen short mails, short enough that a forwarded chain is not a prompt."""

K_OFFER_ROUNDS = 3
"""How hard a look tries to find the values for an offer.

Fewer than a run gets. This runs on a beat over every arriving mail, and an
offer that names most of what it is about is worth far more than one that
takes a minute to name all of it -- the run looks again anyway, with the
patience the run is allowed.

Three and not two: the first round is not the model's to choose (see
`GatherContext`), so two rounds is one search the model actually directs, and
the value is in a sibling mail that has to be found before it can be read."""

K_SUBJECT = 120
"""How much of a request's name travels with the offer. A subject line, not a
forwarded chain of them: `Fwd: Re: Fwd:` prefixes stack, and what a person
needs is enough to tell this request from the three like it."""

K_BECAUSE = 400
"""How much of the request the gather is told, so it knows what it is looking
for. The sentence that asked, not the mailbox."""

K_RECENT = "newer_than:2d -in:chats"
"""What counts as an arrival worth reading.

Two days rather than an hour: a look runs when somebody asks for one, and a
request that arrived over the weekend is still a request.

**No label filter, and three tries to get there.** The intent was "their own
outgoing mail is not a request TO them", and every way Gmail offers to say that
excludes exactly the mail an operator sends themselves -- which is how a person
forwards themselves something to deal with later, and how every test request on
this deployment is written. Measured against the real mailbox, 2026-09-16, on a
self-addressed request sent at 20:34:

    -in:sent -in:chats          does not find it
    in:inbox -in:chats          does not find it -- Gmail files it under Sent,
                                and the thread only APPEARS in the inbox view
    {to:me cc:me}               does not find it -- `to:me` does not match it
    newer_than:2d -in:chats     finds it, first row

So the filter is gone. What it was protecting against remains true and is
smaller than it looked: a mail the operator sent asking somebody ELSE to do the
work can now produce a card. That card is an offer a person presses, so the
cost of being wrong is a card they say no to -- and the same write claim that
stops two runs making one record still stands behind it.

Chats stay out. A chat message is not a request in any sense this reads.
"""

K_REMEMBER = timedelta(days=30)
"""How long a message stays offered-once.

Long enough that a mailbox re-read for a month says nothing twice, short enough
that the ledger does not grow forever. A mail older than this that somehow
comes round again is one nobody acted on in a month, and offering it a second
time is not the worst thing this could do.
"""

K_TEXT = 2000
"""How much of one message is read against the jobs.

A request states itself at the top: a greeting, the ask, the values. What
follows is a quoted thread and a signature block, which is where a model finds
last week's request and offers the job again for a record that already exists.
"""


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Offered:
    """One mail, and the job it turned out to ask for."""

    message: str
    workflow_id: str
    title: str
    values: Mapping[str, str] = field(default_factory=dict)
    missing: Sequence[str] = ()

    subject: str = ""
    """What the request was called, so a conversation about it can say which.

    A deliberate exception to `MailOfferModel`'s rule that the id travels and
    the words do not, and worth naming as one. That rule is about not echoing
    somebody's mail across a boundary to say what the id already says -- and it
    already bends for `values`, because nobody can consent to a write they
    cannot see. A subject is the same category: with four requests for the same
    job open at once, it is the only thing that tells one from another in a
    thread that is no longer standing next to the card."""

    thread: str = ""
    """The mail conversation this request arrived in.

    Carried so the run started from this offer can be found again by a reply to
    it. The person who knows the value a run could not find is usually whoever
    sent the request, and they are not the person with the panel open -- see
    `domain/execution/waiting.py`."""

    too_long: Mapping[str, int] = field(default_factory=dict)
    """The values this job's boxes will not hold, and what they hold instead.

    Known here only because some earlier run found it out the hard way and
    wrote it down. Carried on the OFFER, which is the point: the run already
    refuses a value that will not fit, and refusing at that moment means a
    person pressed, watched half a form fill, and got a question back. The
    limit is known before the press, so it can be said before the press."""


@dataclass(frozen=True, slots=True)
class LookedInTheMail:
    """What one look through the mailbox came to."""

    offered: tuple[Offered, ...] = ()
    read: int = 0
    why: str = ""
    spent: Answer = field(default_factory=Answer)


class FromTheMail:
    """Read the operator's recent mail, and offer the jobs it asks for."""

    def __init__(
        self,
        uow: UnitOfWork,
        tools: ToolCaller,
        asker: Asker | None,
        *,
        model: str,
        gather: GatherContext | None = None,
        clock: Clock | None = None,
        ids: IdFactory | None = None,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._asker = asker
        self._model = model
        self._gather = gather
        # Only for closing a question a reply has answered, which is the one
        # thing this door writes into the operator's own conversation. Optional
        # so nothing that builds this for a test has to grow two arguments to
        # go on testing what it was testing.
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, *, limit: int = K_LOOK) -> LookedInTheMail:
        """One look. Nothing runs, and nothing is written down about the mail.

        What reaches storage is an offer in this operator's own thread -- the
        job, the values, what is missing -- and a claimed key per message id.
        The mail's own words are not kept: they were read out of somebody's
        mailbox to decide one thing, and `ChatReading` has no field for them
        for the same reason.
        """
        # The one guard, in the use case rather than in the container: a
        # factory that raised would make a deployment with no key unbuildable
        # instead of refusing at the one call that actually needs a model.
        asker = asker_or_refuse(self._asker)
        now = datetime.now(tz=UTC)
        async with self._uow as uow:
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
            arrivals = await self._recent(ctx, limit)
        except ToolsUnavailable as gone:
            return LookedInTheMail(why=f"the mailbox could not be reached: {gone}")

        offered: list[Offered] = []
        spent = Answer()
        read = 0
        # Read, asked for a job, and dropped because the reading could not tell
        # which job. Counted rather than swallowed: see `_sentence`.
        unsure = 0
        tenant = ctx.tenant_id.value
        for message in arrivals:
            if not await self._first_time(ctx, message, now=now):
                continue
            try:
                said, thread, subject = await self._body(ctx, message)
            except ToolsUnavailable as gone:
                return LookedInTheMail(
                    offered=tuple(offered), read=read, why=str(gone), spent=spent
                )
            if not said:
                continue
            read += 1
            # A reply to a request this system already acted on, and could not
            # finish.
            #
            # The thread decides the job here, and the model does not get
            # asked. Two reasons, and the second is the one that matters: the
            # run waiting on this conversation already agreed which job it is,
            # so a reading would be re-deciding a settled question -- and a
            # bare reply is the exact sentence a reading cannot make anything
            # of. Somebody answering "GU9" to "what should the Customer Type
            # be?" has written two words with no job in them: `understand`
            # answers `sure=False` or nothing at all, the arrival is dropped,
            # and the id is already claimed so it is dropped for good. The
            # answer would be lost at precisely the moment it arrived.
            back = await self._answering(ctx, thread)
            if back is not None:
                offered.append(
                    await self._carrying_on(ctx, message, back, said, thread, subject, titles, held)
                )
                continue
            # Or a question standing in the conversation that this answers.
            asked = await self._was_asked(ctx, thread)
            if asked is not None:
                offered.append(
                    await self._answered_by_mail(ctx, message, asked, said, thread, subject, held)
                )
                continue
            got = await understand(said, workflows, asker, self._model, asked_by)
            spent = _also(spent, got.answer)
            # Silence where it is not sure, and where it named no job at all.
            # A card about a delivery notice is worse than no card: the person
            # stops reading the ones that matter.
            if got.workflow_id is None:
                logger.info("%s: read a mail that asks for no job this tenant holds", tenant)
                continue
            if not got.sure:
                # Which other jobs it might have meant, because that is the
                # whole of why it said nothing. Measured on the deployment,
                # 2026-09-17: this tenant holds TWO workflows called `Create a
                # Customer Type` -- one with six steps and sixty-one runs, one
                # with two steps and none -- so every mail asking for one named
                # both, `sure` went false, and the mail path was silent about
                # the job the rig had otherwise learned to do. Nothing anywhere
                # said so.
                unsure += 1
                logger.info(
                    "%s: read a mail asking for %s but could not tell it from %s",
                    tenant,
                    titles.get(got.workflow_id, got.workflow_id),
                    ", ".join(titles.get(one, one) for one in got.also) or "another job",
                )
                continue
            # The values it is about, before it is offered.
            #
            # A request rarely carries them: "please create the customer type
            # as discussed" is the whole of it, and what to create is in the
            # mail before it. So the reading came back with the job and two
            # missing values, and the card said "Create a Customer Type -- want
            # me to do it?" with nothing to tell one from another. Four of them
            # stacked up on the deployment, 2026-09-18, and they were the same
            # sentence four times.
            #
            # Nobody can consent to a write they cannot see. The run gathers
            # these anyway, a moment after the press -- this is the same work
            # moved to where the decision is actually made, so a wrong reading
            # is caught before the record instead of after it.
            values, missing = dict(got.values), list(got.missing)
            # The conversation first, because that is where the answer is.
            #
            # A reply that says "as discussed" was discussed in the mail above
            # it. Reading the thread is one call and no guessing; the gather
            # below searches the whole mailbox with a query a model writes, and
            # on this mailbox that came back empty about a value one mail away.
            if missing:
                # Every way this can end, said. It came up short four times
                # running on the deployment and each round told me one more
                # thing, because each round only one branch of this could
                # speak. A step that can fail five ways and reports one of them
                # is a step nobody can debug -- which is the lesson the
                # execution ladder already learned, in the same week.
                job_ = titles.get(got.workflow_id, got.workflow_id)
                if not thread:
                    logger.info("%s: %s -- the mail names no conversation", tenant, job_)
                else:
                    whole = await self._conversation(ctx, thread)
                    if not whole:
                        logger.info("%s: %s -- the conversation read back empty", tenant, job_)
                    elif whole == said:
                        logger.info("%s: %s -- the conversation is only this mail", tenant, job_)
                    else:
                        again = await understand(whole, workflows, asker, self._model, asked_by)
                        spent = _also(spent, again.answer)
                        if again.workflow_id != got.workflow_id:
                            # A thread that wandered onto another subject is not
                            # more evidence about this one.
                            logger.info(
                                "%s: %s -- the conversation read as %s instead",
                                tenant,
                                job_,
                                titles.get(again.workflow_id or "", again.workflow_id)
                                or "no job at all",
                            )
                        else:
                            values |= dict(again.values)
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
                # What the gather came back with, because an offer that names
                # nothing and an offer that was never gathered for look the
                # same from outside. Names and counts, never a value: this line
                # is about whether the mechanism worked.
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
                )
            )
        looked = LookedInTheMail(
            offered=await self._what_will_not_fit(ctx, offered, workflows),
            read=read,
            why=_sentence(offered, read, unsure),
            spent=spent,
        )
        # What the look CAME TO, not only what it threw away.
        #
        # The drops have been logged since the sentence was fixed, and nothing
        # logged a kept offer -- so "no line for that message" was the only
        # evidence an offer had been made, and absence of evidence is not it.
        # Twice on 2026-09-17 that reading sent me looking for a card in a
        # panel when I had no idea whether one had ever been offered.
        logger.info(
            "%s: looked in the mail -- %d read, %d offered (%s)",
            tenant,
            read,
            len(offered),
            looked.why,
        )
        return looked

    async def _answering(self, ctx: RequestContext, thread: str) -> WorkflowRun | None:
        """The run still waiting to hear back on this conversation, if any.

        Still waiting: a run whose patience has run out is not holding this
        open any more, and reading a reply into it would start a write somebody
        asked for a week ago and has long since done by hand. Such an arrival
        falls through to the ordinary reading, which is the right answer for it
        -- a fresh request on an old thread is a fresh request.
        """
        if not thread.strip():
            return None
        async with self._uow as uow:
            waiting = await uow.workflow_runs.waiting_on(
                ctx.tenant_id, server=SERVER, thread=thread
            )
        if waiting is None or not still_waiting(read_wait(waiting.awaiting), datetime.now(tz=UTC)):
            return None
        return waiting

    async def _was_asked(self, ctx: RequestContext, thread: str) -> Pending | None:
        """A question standing in the operator's conversation about this mail.

        The other half of `_answering`, and the half the reply actually lands
        in. A run is only waiting when a RUN went looking and came back short;
        an offer that could not be answered from the mail asks before anything
        starts, so the commonest shape -- a request with a field missing --
        produces a question and no run at all.

        Wired only to the run, a reply to that question fell through to the
        ordinary reading, where "the code is GPX" names no job, is dropped, and
        is dropped for good: the message id is claimed before it is read. The
        answer would be lost at the moment it arrived, which is the exact
        failure the whole path exists to prevent.

        The operator's own conversation, because that is where the question
        was put and this look runs as them.
        """
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
        """The waiting run's offer again, with whatever the reply added.

        Everything that run established rides along, which is the whole point
        of finding it: the operator pressed once, the gather spent its rounds,
        and a second card starting from nothing would ask them to do all of it
        again over one missing word.

        What the reply itself says is read by the ordinary gather, against the
        thread it arrived in -- the same call, with the same rounds, now
        looking at a conversation that contains the answer.
        """
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
        """The standing question, with whatever the reply answered of it.

        **A card and not a run**, and the difference is consent rather than
        caution. Everything a job writes has been on a card the operator read
        before pressing -- that is what `2.8` and the limit work are for, and
        what "the card says what it will write" means. A value that arrives
        AFTER the press has been read by nobody: the operator authorised this
        job with the values they could see, not whatever later turns up in a
        mailbox.

        It is the same reasoning the panel's own answer does NOT need. There,
        the person supplying the value is the person who pressed; here they are
        two different people, and the second is outside every system this
        company runs.

        So the reply is read, the value is filled in, and the card comes back
        naming it. One press, on something visible.
        """
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
        await self._the_question_is_answered(ctx, asked, values, missing, said_by=subject)
        return Offered(
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
        """The values this reply actually states, read out of the reply.

        The one thing neither reply path did. A reply is the answer to a
        question this system asked, and both paths handed it to the gather --
        which does not READ it. `because` is a search QUERY there: the words
        somebody wrote are typed into a mailbox search, the search comes back
        with the thread or with nothing, and the value sitting in the sentence
        is never looked at. Measured on the deployment 2026-09-18: a reply
        saying `customer type :- QQI` to a question asking for Customer Type
        was logged `a reply answers the question standing on ... (0 of 1)`, and
        the card came back asking the same thing again.

        The job is known here -- the thread settled it -- so the reading is
        given that one job and nothing else to choose between. It is asked for
        values, not for which job this is: re-deciding a settled question on
        two words like `QQI` is how a bare answer ends up read as no job at
        all and dropped.

        Empty for every ordinary reason, and the gather still runs after it: a
        reply that says nothing useful is the case the mailbox search exists
        for.
        """
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
    ) -> None:
        """Close the standing question, because a reply has answered it.

        The card is built and the conversation was left asking. So the panel
        said two things at once -- here is NGSL, press to run it, and also what
        should Customer Type be -- which is a system that does not know what it
        knows. Seen on the deployment 2026-09-18.

        `pending_job` reads the last thing the ASSISTANT decided, so what ends
        a question is the assistant deciding something else. Where the reply
        answered everything that was outstanding, that is a note saying so.
        Where it answered some of it, the question that is left is asked again
        with the new values on it, so the thread carries the progress rather
        than repeating its first sentence.

        Silent on every failure: a conversation that could not be written to
        is a stale question, and a stale question is not worth losing the card
        that answers it.
        """
        if self._clock is None or self._ids is None:
            return
        try:
            found = await ReadThreads(self._uow).current(ctx)
            if found is None:
                return
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
                f" {question(still)}" if missing else " It is on your Home tab to start."
            )
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=ctx.principal_id,
                text=said,
                # ASSISTANT either way: this is the thing that decides whether a
                # question is still standing, and a SYSTEM note leaves the old
                # one to be found by the next sentence somebody types.
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
                    else {"kind": Said.NOTE, "workflow_id": still.workflow_id}
                ),
            )
        except Exception:
            logger.exception("the answered question could not be closed")

    async def _what_will_not_fit(
        self, ctx: RequestContext, offered: Sequence[Offered], jobs: Sequence[Workflow]
    ) -> tuple[Offered, ...]:
        """Each offer, told which of its values its own boxes are too small for.

        One read per job rather than per offer: a mailbox holding four requests
        for the same job is the ordinary case, and it is the same answer four
        times.

        A job nothing has been learnt about comes back exactly as it went in,
        which is most of them -- a limit exists only where a run has hit one.
        """
        by_id = {one.id: one for one in jobs}
        limits: dict[str, dict[str, int]] = {}
        for workflow_id in sorted({one.workflow_id for one in offered}):
            job = by_id.get(workflow_id)
            if job is None:
                continue
            async with self._uow as uow:
                learnt = await uow.workflows.learned_for(workflow_id)
            found = limits_for(
                job.steps,
                learnt,
                # And what this job's fields are DOCUMENTED to hold, for the
                # boxes no run has hit yet. The whole value of asking before
                # the press is lost if the first request too long for a field
                # still has to be sent to find that out.
                await declared_limits(
                    self._uow,
                    ctx.tenant_id,
                    names_of(job),
                    await screen_for(self._uow, ctx.tenant_id, job),
                ),
            )
            if found:
                limits[workflow_id] = found
        return tuple(
            one
            if one.workflow_id not in limits
            else replace(one, too_long=too_long(one.values, limits[one.workflow_id]))
            for one in offered
        )

    async def _recent(self, ctx: RequestContext, limit: int) -> list[str]:
        """The newest message ids, as this operator. Ids only: what each one
        says is read one at a time below, and a search answer carries a snippet
        that is not enough to decide on."""
        answered = await self._tools.call(
            ctx.tenant_id,
            ctx.principal_id,
            SERVER,
            "search_threads",
            {"query": K_RECENT, "limit": str(limit)},
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return []
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list):
            return []
        return [
            str(row["id"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        ][:limit]

    async def _body(self, ctx: RequestContext, message: str) -> tuple[str, str, str]:
        """What one message says, the conversation it belongs to, and its name.

        The thread beside the words because a request rarely carries what it is
        about: "as discussed" was discussed in the mail above it, and which
        mail that is, is a fact Gmail already knows.

        The subject beside both because a conversation about this request has
        to be able to say which request. See `Offered.subject`.
        """
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return "", "", ""
        if not isinstance(said, dict):
            return "", "", ""
        whole = " ".join(
            str(said.get(part) or "").strip() for part in ("subject", "body", "snippet")
        )
        whole = " ".join(whole.split())
        return (
            whole[:K_TEXT],
            str(said.get("thread_id") or ""),
            " ".join(str(said.get("subject") or "").split())[:K_SUBJECT],
        )

    async def _conversation(self, ctx: RequestContext, thread: str) -> str:
        """Every mail in one conversation, as one piece of text.

        The conversation and not a search. A request names no values -- "please
        create the customer type as discussed" -- and the values are in the mail
        it replies to, which Gmail already knows about: it is the same thread.
        Searching the mailbox for it is guessing at something nobody has to
        guess at, and on a mailbox holding seventeen near-identical threads the
        guess came back "the mailbox holds none of the values this job needs"
        about a value sitting one mail away. Measured on the deployment,
        2026-09-17 at 21:26.
        """
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

    async def _first_time(self, ctx: RequestContext, message: str, *, now: datetime) -> bool:
        """Whether this message has been offered before.

        The claim ledger rather than a table of its own: this is the shape it
        already keeps -- a key, claimed once, with a window -- and a second
        store for "have I seen this" is a second store to migrate.

        Claimed BEFORE the reading, so a look that fails half way through does
        not read the same mail again on the next one. The cost of that is a
        mail nobody was offered after a crash; the cost of the other order is a
        model call per look per message, forever.
        """
        async with self._uow as uow:
            first = await uow.tool_calls.remember(
                ctx.tenant_id,
                f"mail:{ctx.principal_id.value}:{message}",
                tool="read a mail for what it asks",
                at=now,
                stale_after=K_REMEMBER,
            )
            await uow.commit()
        return first


def _sentence(offered: Sequence[Offered], read: int, unsure: int = 0) -> str:
    """What happened, for a person reading the result rather than the code."""
    if not read:
        return "no mail has arrived since the last look"
    if not offered and unsure:
        # NOT "none of them asks for a job", which is what this said and which
        # was false: one of them asked, and the reading could not tell which of
        # two jobs it meant. A look that reports the wrong absence is a look
        # nobody investigates -- the tenant had two workflows with one name for
        # a day, and this sentence is why nobody knew.
        return f"read {read}, and {unsure} asked for a job this tenant holds more than one of"
    if not offered:
        return f"read {read}, and none of them asks for a job this tenant holds"
    return "offered " + ", ".join(one.title for one in offered)


def _also(running: Answer, answer: Answer) -> Answer:
    """What the readings came to, totalled. Kept because every other loop here
    reports it and the spend line reads it, not as a limit on anything."""
    return Answer(
        in_tokens=running.in_tokens + answer.in_tokens,
        out_tokens=running.out_tokens + answer.out_tokens,
        thought_tokens=running.thought_tokens + answer.thought_tokens,
        cost_usd=running.cost_usd + answer.cost_usd,
        unpriced=running.unpriced or answer.unpriced,
    )


__all__ = ["FromTheMail", "LookedInTheMail", "Offered"]
