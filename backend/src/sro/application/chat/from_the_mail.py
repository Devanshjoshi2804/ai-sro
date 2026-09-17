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
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sro.application.chat.understand import understand
from sro.application.context import RequestContext
from sro.application.execution.gather import GatherContext
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.shared.prices import Answer

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
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._asker = asker
        self._model = model
        self._gather = gather

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
                said, thread = await self._body(ctx, message)
            except ToolsUnavailable as gone:
                return LookedInTheMail(
                    offered=tuple(offered), read=read, why=str(gone), spent=spent
                )
            if not said:
                continue
            read += 1
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
            if missing and not thread:
                # The two ways this can come up short are not the same fault:
                # a request whose conversation was read and did not hold the
                # values, and a request that arrived with no conversation to
                # read. The second means the thread id never reached here.
                logger.info(
                    "%s: %s is missing %d value(s) and the mail names no conversation",
                    tenant,
                    titles.get(got.workflow_id, got.workflow_id),
                    len(missing),
                )
            if missing and thread:
                whole = await self._conversation(ctx, thread)
                if whole and whole != said:
                    again = await understand(whole, workflows, asker, self._model, asked_by)
                    spent = _also(spent, again.answer)
                    if again.workflow_id == got.workflow_id:
                        values |= dict(again.values)
                        missing = [name for name in missing if name not in values]
                        logger.info(
                            "%s: read the whole conversation for %s -- %d of %d found",
                            tenant,
                            titles.get(got.workflow_id, got.workflow_id),
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
                )
            )
        looked = LookedInTheMail(
            offered=tuple(offered), read=read, why=_sentence(offered, read, unsure), spent=spent
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

    async def _body(self, ctx: RequestContext, message: str) -> tuple[str, str]:
        """What one message says, and the conversation it belongs to.

        The thread beside the words because a request rarely carries what it is
        about: "as discussed" was discussed in the mail above it, and which
        mail that is, is a fact Gmail already knows.
        """
        answered = await self._tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        try:
            said = json.loads(answered.text)
        except ValueError:
            return "", ""
        if not isinstance(said, dict):
            return "", ""
        whole = " ".join(
            str(said.get(part) or "").strip() for part in ("subject", "body", "snippet")
        )
        whole = " ".join(whole.split())
        return whole[:K_TEXT], str(said.get("thread_id") or "")

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
