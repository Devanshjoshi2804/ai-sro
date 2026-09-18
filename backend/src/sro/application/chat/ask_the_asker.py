"""Draft a mail to whoever asked, and -- separately -- send the one approved.

Two use cases in one module because they are two halves of one rule, and the
rule is the reason this exists at all: **what drafts never sends, and what
sends never drafts.** A mail cannot be unsent, it leaves the company over the
operator's name, and the only thing standing between a model's reading of a
situation and somebody's inbox is a person who read the words first. Splitting
them is what makes that structural rather than a promise -- there is no path
through `DraftForTheAsker` that reaches the mailbox.

The case: a request arrives naming a description and no code. The run goes
looking, the thread does not say either, and the run ends short. The panel
asks the operator, which is right and often enough -- but the operator did not
write the request and may not know. The person who does is whoever sent it,
and until now nothing could reach them.

**One draft per run.** A run that stopped twice does not write twice, and a
person does not get two mails about one request. The check is the run's own
row rather than a counter here, because a worker restart must not buy anybody
a second mail.
"""

from __future__ import annotations

import json
import logging

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.from_the_mail import K_REMEMBER
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.chat.asking import Pending
from sro.domain.chat.asking_the_asker import draft_for, worth_asking
from sro.domain.chat.thread import Message, Speaker, ThreadId
from sro.domain.execution.waiting import read_wait
from sro.domain.shared.identifiers import PrincipalId

logger = logging.getLogger(__name__)

SERVER = "gmail"

DRAFTED = "mail_draft"
"""The decision kind of a mail written and not sent. Named here because two
sides read it: this door writes it, and the panel draws the words with a press
under them."""


class DraftForTheAsker:
    """Write the mail, put it in front of the operator, and stop.

    Nothing here can send. The tool caller it holds is used to READ the
    conversation -- who asked, and what the message id is to reply to -- and
    the only write it makes is into the operator's own thread.
    """

    def __init__(self, uow: UnitOfWork, tools: ToolCaller, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock
        self._ids = ids

    async def execute(
        self, ctx: RequestContext, pending: Pending, *, thread: str = "", run_id: str = ""
    ) -> bool:
        """Whether a draft was put in front of somebody.

        Called from both places a job stops short of a value, because there are
        two and only one of them has a run behind it. A card that cannot be
        answered from what the mail said asks in the conversation before
        anything starts; a run that goes looking and comes back empty asks
        after. The person who can answer is the same person either way, and
        wiring this only to the second made it unreachable for the case it was
        built for -- a mail with no code in it never reaches a run.

        `thread` is the conversation to write into, and it wins over the run's
        own: an offer has one before any run exists.

        False for every ordinary reason -- no mailbox behind it, nothing
        missing, somebody already asked. None of those is a failure.
        """
        if not worth_asking(pending):
            return False
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id) if run_id else None
        waiting = read_wait(run.awaiting) if run else None
        conversation = thread.strip() or (waiting.thread if waiting else "")
        if not conversation:
            return False
        # One per run, read off the row rather than counted here: a worker that
        # restarted between two stops must not buy anybody a second mail.
        if run is not None and run.asked_the_asker:
            logger.info("%s: %s has already asked whoever sent it", ctx.tenant_id.value, run_id)
            return False
        # And one per REQUEST, for the half that has no run yet. Two presses on
        # one card would otherwise put two drafts in front of somebody, and the
        # second is a mail they can send after the first has gone.
        if await self._already_drafted(ctx, conversation):
            logger.info("%s: %s is already drafted for", ctx.tenant_id.value, conversation)
            return False

        asked_by, replying_to, about = await self._who_asked(ctx, conversation)
        if not asked_by:
            logger.info(
                "%s: %s has nobody to ask -- the conversation names no sender",
                ctx.tenant_id.value,
                run_id,
            )
            return False

        subject, body = draft_for(pending, about=about, signed=ctx.principal_id.value)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(run.started_by)
            if run and run.started_by
            else ctx.principal_id,
            text=f"I can ask {asked_by}. This is what I would send — read it first.",
            # SYSTEM, not ASSISTANT: `pending_job` reads back the last thing the
            # ASSISTANT decided, and a draft standing where the question should
            # be would eat the operator's next sentence.
            speaker=Speaker.SYSTEM,
            decision={
                "kind": DRAFTED,
                "run_id": run_id,
                "to": asked_by,
                "subject": subject,
                "body": body,
                "thread": conversation,
                "in_reply_to": replying_to,
            },
        )
        logger.info(
            "%s: drafted a mail to %s about %s",
            ctx.tenant_id.value,
            asked_by,
            run_id or conversation,
        )
        return True

    async def _already_drafted(self, ctx: RequestContext, conversation: str) -> bool:
        """Whether somebody already has a draft in front of them for this mail.

        Read off the operator's own thread, which is where the draft was put:
        there is no run to hang a flag on before one starts, and the thread is
        already the record of what has been said. A draft that was SENT is not
        a reason to refuse another either -- the run column covers that, and
        this covers the window before it exists.
        """
        found = await ReadThreads(self._uow).current(ctx)
        if found is None:
            return False
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, found.id)
        return any(
            isinstance(message.decision, dict)
            and message.decision.get("kind") == DRAFTED
            and message.decision.get("thread") == conversation
            for message in thread.messages
        )

    async def _who_asked(self, ctx: RequestContext, thread: str) -> tuple[str, str, str]:
        """Who to answer, which message to answer, and what it was called.

        The FIRST message of the conversation, not the last: a thread the
        operator has replied to would otherwise have this system writing to the
        operator about the operator's own request. The first message is the
        request, and whoever sent it is who to ask.
        """
        try:
            answered = await self._tools.call(
                ctx.tenant_id, ctx.principal_id, SERVER, "get_thread", {"id": thread}
            )
        except ToolsUnavailable as gone:
            logger.info("%s: the conversation could not be read: %s", ctx.tenant_id.value, gone)
            return "", "", ""
        try:
            said = json.loads(answered.text)
        except ValueError:
            return "", "", ""
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list) or not rows:
            return "", "", ""
        first = rows[0] if isinstance(rows[0], dict) else {}
        return (
            _address(str(first.get("from") or "")),
            str(first.get("rfc822_message_id") or first.get("id") or ""),
            " ".join(str(first.get("subject") or "").split()),
        )


def _address(sender: str) -> str:
    """The address out of `Tanisha Pradhan <tanisha@example.com>`.

    A display name is not something to send to, and a header with none is
    already an address. Nothing is invented where neither is there: an empty
    answer means nobody to ask, which is a thing this door says rather than
    guesses past.
    """
    said = sender.strip()
    if "<" in said and ">" in said:
        said = said[said.index("<") + 1 : said.index(">")].strip()
    return said if "@" in said else ""


class SendTheDraft:
    """Send the mail the operator read, and nothing else.

    **The words are taken from the thread, never from the caller.** The panel
    sends an id; this re-reads the draft that was actually put in front of
    somebody and sends that. A door that sent a body handed to it would be a
    door where the words that go out and the words that were read are two
    different things, and every guarantee this system makes about a person
    having seen what they authorised would rest on a browser being honest.

    The press is the authorisation and it is the only one. Nothing here
    decides that a mail should go -- it decides that this mail, which somebody
    has read, may.
    """

    def __init__(self, uow: UnitOfWork, tools: ToolCaller, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, thread_id: ThreadId, message_id: str) -> str:
        """The address it went to, or `""` where nothing was sent.

        Raises nothing for an ordinary refusal. A draft already sent, a draft
        nobody can find, a run that has since been asked about another way --
        all are reasons not to send, and none of them is an error worth a 500.
        """
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
        draft = _the_draft(thread.messages, message_id)
        if draft is None:
            logger.info("%s: no draft to send under %s", ctx.tenant_id.value, message_id)
            return ""

        # The press itself, claimed before anything else.
        #
        # The run column below is one mail per RUN, and it is the only claim
        # there was -- so the half with no run behind it had none at all. A
        # card asks before any run exists (`run_id` is ""), `run` is None, the
        # check is skipped, and every press sends another mail. Measured on the
        # live deployment 2026-09-18: two identical mails to one person about
        # one request, 15:05:34 and 15:09:06, both logged `asked ... about `
        # with nothing after the `about`.
        #
        # Keyed by the DRAFT, which exists on both paths and is unique to the
        # words somebody actually read.
        if not await self._claim(ctx, message_id):
            logger.info("%s: the draft %s has already been sent", ctx.tenant_id.value, message_id)
            return ""

        run_id = str(draft.get("run_id") or "")
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id) if run_id else None
            # Claimed before the send, not after. Between a check and a mailbox
            # sits a network call, and a second press landing in that gap is a
            # second mail about one request -- which is the one thing the
            # column exists to stop.
            if run is not None:
                if run.asked_the_asker:
                    logger.info("%s: %s was already asked", ctx.tenant_id.value, run_id)
                    return ""
                run.asked_the_asker = True
                await uow.workflow_runs.save(run)
                await uow.commit()

        to = str(draft.get("to") or "")
        try:
            answered = await self._tools.call(
                ctx.tenant_id,
                ctx.principal_id,
                SERVER,
                "send_message",
                {
                    "to": to,
                    "subject": str(draft.get("subject") or ""),
                    "body": str(draft.get("body") or ""),
                    # Inside the conversation it answers. A reply that starts
                    # its own thread cannot be matched back to the run waiting
                    # on it, so the person answers into a void.
                    "thread_id": str(draft.get("thread") or ""),
                    "in_reply_to": str(draft.get("in_reply_to") or ""),
                },
            )
        except ToolsUnavailable as gone:
            # The claim stands. A send that may have gone out and cannot be
            # shown to have is not one to try again -- the same rule the write
            # ladder keeps, and for a stronger reason: a duplicate mail cannot
            # be deleted afterwards.
            logger.warning(
                "%s: the mail to %s may not have gone: %s", ctx.tenant_id.value, to, gone
            )
            await self._say(
                ctx,
                thread_id,
                f"I could not reach the mailbox to write to {to}.",
                run_id,
                message_id,
                sent=False,
            )
            return ""

        # And the mail this system just wrote is not a request TO it.
        #
        # The look reads the mailbox for anything asking for a job, and what it
        # was handed back was our own question: "I am working on Create a
        # Customer Type... I still need Customer Type" reads, correctly, as
        # somebody asking for a customer type. Measured on the deployment
        # 2026-09-18 -- the mail went out and the next look offered a card for
        # it, which is this system asking itself to do the thing it had just
        # asked a person about.
        #
        # Claimed in the same ledger a read claims, because it is the same
        # question -- "have I dealt with this message" -- and a second store
        # for it is a second store to keep in step.
        await self._never_read(ctx, answered)
        await self._say(
            ctx,
            thread_id,
            f"Asked {to}. I will carry on when they reply.",
            run_id,
            message_id,
            sent=True,
        )
        logger.info("%s: asked %s about %s", ctx.tenant_id.value, to, run_id)
        return to

    async def _claim(self, ctx: RequestContext, message_id: str) -> bool:
        """Take this draft, or say somebody already has it.

        Never given back. A send that timed out may well have landed, and a
        claim released on failure would retry it into a second mail -- the same
        rule the connector ledger keeps everywhere else, and for the strongest
        reason it has: a duplicate mail cannot be deleted afterwards.
        """
        async with self._uow as uow:
            mine = await uow.tool_calls.remember(
                ctx.tenant_id,
                f"draft:{ctx.principal_id.value}:{message_id}",
                tool="a mail drafted for whoever asked, sent once",
                at=self._clock.now(),
            )
            await uow.commit()
        return mine

    async def _never_read(self, ctx: RequestContext, answered: object) -> None:
        """Claim the id of the mail just sent, so no look ever reads it.

        Silent about everything it cannot do. A connector that answered without
        an id, an answer that is not JSON, a ledger that refuses -- none of
        them is a reason to tell somebody their mail did not go, because it
        did. The cost of missing this is one card somebody dismisses.
        """
        try:
            said = json.loads(getattr(answered, "text", "") or "{}")
            sent_id = str(said.get("id") or "") if isinstance(said, dict) else ""
            if not sent_id:
                return
            async with self._uow as uow:
                await uow.tool_calls.remember(
                    ctx.tenant_id,
                    f"mail:{ctx.principal_id.value}:{sent_id}",
                    tool="a mail this system sent, which is not a request",
                    at=self._clock.now(),
                    stale_after=K_REMEMBER,
                )
                await uow.commit()
        except Exception:
            logger.exception("the sent mail could not be claimed and may be read as a request")

    async def _say(
        self,
        ctx: RequestContext,
        thread_id: ThreadId,
        text: str,
        run_id: str = "",
        draft_id: str = "",
        *,
        sent: bool,
    ) -> None:
        """What happened, in the conversation the draft was read in.

        `sent` is whether it actually went. Both answers end the press -- the
        claim is taken either way, and a send that may have gone out is not one
        to try again -- but the row must not say a mail was sent when nobody
        knows whether it was. One kind, one honest flag, rather than a line
        reading `mail_sent` under the words "I could not reach the mailbox".
        """
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.SYSTEM,
                    text=text,
                    said_at=self._clock.now(),
                    # The run AND the draft, so the panel can stop offering a
                    # press under words that have already left. The run is
                    # empty on the half that asks before any run exists, and a
                    # panel keyed only on that went on showing `Send it` under
                    # a mail already in somebody's inbox.
                    decision={
                        "kind": SENT,
                        "run_id": run_id,
                        "draft_id": draft_id,
                        "sent": sent,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()


SENT = "mail_sent"
"""The decision kind of a draft that is spent, sent or not.

The panel reads it to stop drawing a press under words that have already left
-- or that may have. `sent` on the decision says which, because the claim is
taken before the mailbox is reached and a send that cannot be shown to have
failed must not be retried either."""


def _the_draft(messages: object, message_id: str) -> dict[str, object] | None:
    """The drafted mail with that id, if it is still the last word on it.

    By id and not "the newest draft": two runs can both be waiting, and a press
    on the older card must not send the newer mail.
    """
    for message in reversed(list(messages if isinstance(messages, tuple | list) else ())):
        decision = getattr(message, "decision", None)
        if not isinstance(decision, dict) or decision.get("kind") != DRAFTED:
            continue
        # Both sides through `str`: a message id is an `Identifier`, and a
        # caller holding one compares unequal to the same id read back off a
        # row as text. The two were never going to match by accident, which is
        # the worst kind of mismatch -- every draft would quietly refuse.
        if str(getattr(message, "id", "")) == str(message_id):
            return decision
    return None


__all__ = ["DRAFTED", "SENT", "DraftForTheAsker", "SendTheDraft"]
