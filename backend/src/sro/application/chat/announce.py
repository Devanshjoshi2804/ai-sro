"""Saying, in the operator's own conversation, that something happened.

An offer is a `SYSTEM` message: "you have done this 3 times, want me to do the
next one?". Until now nothing said what came of it, so the console showed every
offer permanently unanswered, and a reopened panel drew both buttons again as
though the question were still open.

So the answer is a message too. Not a mutation of the offer -- a `Message` is a
record of something that was said, and editing one to report its own answer
would make the thread a state machine rather than an account of what happened.
"""

from __future__ import annotations

from sro.application.chat.converse import StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Speaker
from sro.domain.shared.identifiers import PrincipalId


class SayWhatHappened:
    """Append a `SYSTEM` message to the conversation one operator is in.

    Deliberately not shared with `ProposeAboutCandidates._offer`, which writes
    its message and the candidate's `offered_at` in one transaction: written
    and not recorded means the sweep says it again, recorded and not written
    means it is never said at all. That coupling belongs to offering, and
    folding it into a general helper would hide it.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        for_operator: PrincipalId,
        text: str,
        decision: dict[str, object],
    ) -> None:
        """Say it in `for_operator`'s thread, not the caller's.

        The two differ whenever something happens on an operator's behalf, and
        a message in the wrong conversation is worse than none: the operator
        never sees it, and somebody else sees work they did not do.
        """
        owner = RequestContext(ctx.tenant_id, for_operator)
        found = await ReadThreads(self._uow).current(owner) or await StartThread(
            self._uow, self._clock, self._ids
        ).execute(owner)
        async with self._uow as uow:
            thread = await uow.threads.get(owner.tenant_id, found.id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.SYSTEM,
                    text=text,
                    said_at=self._clock.now(),
                    decision=decision,
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
