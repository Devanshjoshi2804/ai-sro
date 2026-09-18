"""Turn an offer that cannot simply run into a question in the conversation.

The card used to grow boxes. One text input per name it still wanted, drawn
under the sentence, and the press disabled until they were full -- and
`asking.py` already says what is wrong with that, at length, because the run
path learned it first:

    It asks everybody for what it usually finds by itself, and on `Create a
    Customer Type` it asked four times for two values, because that job
    declares each field twice -- the label a person reads and the body key a
    form posts.

Then the limit work added a second box for a different reason: a value that
will not fit, pre-filled, with the number beside it. Better than silence and
still the same shape -- a form, in a card, in a panel that is already a
conversation.

So the card asks the way everything else here asks. A press that cannot start
the job writes the question into the operator's own thread, and
`converse._answer_the_question` takes it from there: one question, one answer,
the next question, and when the last one lands a `job` decision with `resume`
on it that the browser starts. That loop is built, it is tested, and until now
the only way into it was to type a yes in the chat -- the card, which is where
people actually press, went around it.

**Nothing is decided here.** This writes a question and returns. What the
person says next is read by the same door that reads everything else they say,
against the same pending state, so there is one set of rules about what an
answer means rather than two.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.asking import NEEDS, Pending, question, unusable
from sro.domain.chat.thread import Speaker
from sro.domain.shared.identifiers import PrincipalId

logger = logging.getLogger(__name__)


class AskAboutTheOffer:
    """Ask, in the operator's own conversation, for what an offer still needs."""

    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, pending: Pending) -> str:
        """The question that was asked, or `""` where there was nothing to ask.

        Empty rather than an error for an offer that needs nothing: a caller
        that got here about a job which turned out to be ready should start it,
        and a refusal would make that an error path instead of the ordinary
        one.
        """
        # What is outstanding is what nobody supplied AND what was supplied in
        # a form the box will not take.
        #
        # The second half is the case this door was built for and the case it
        # first got wrong: an offer read out of a mail carrying a ten-character
        # code for a four-character field has nothing MISSING, so it read as
        # ready and asked nothing at all. Measured on the deployment
        # 2026-09-18: `asked about mail_1a0b3da3e11ad236 in the conversation:
        # nothing to ask`, on the one press this exists to answer.
        #
        # Order kept and duplicates dropped: a name can be both unsupplied and
        # capped, and asking for it twice is the form this replaces.
        pending = replace(
            pending,
            missing=tuple(
                dict.fromkeys((*pending.missing, *unusable(pending.values, pending.limits)))
            ),
        )
        if pending.ready:
            return ""
        asked = question(pending)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            # The person who pressed. An offer is answered by whoever it was
            # put in front of, and a question in somebody else's conversation
            # is one they never see.
            for_operator=PrincipalId(ctx.principal_id.value),
            text=asked,
            # A question, not an announcement -- see `SayWhatHappened.execute`.
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": NEEDS,
                "workflow_id": pending.workflow_id,
                "title": pending.title,
                "values": dict(pending.values),
                "missing": list(pending.missing),
                "items": [dict(one) for one in pending.items],
                # What the boxes hold, so the next question can say why it is
                # being asked -- and so an answer that still will not fit is
                # refused rather than carried into the form.
                "limits": dict(pending.limits),
                "watched": pending.watched,
            },
        )
        logger.info(
            "%s: asking about %s in the conversation -- %d value(s) still wanted",
            ctx.tenant_id.value,
            pending.title,
            len(pending.missing),
        )
        return asked


__all__ = ["AskAboutTheOffer"]
