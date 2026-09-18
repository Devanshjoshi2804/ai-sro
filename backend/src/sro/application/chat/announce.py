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
        speaker: Speaker = Speaker.SYSTEM,
    ) -> None:
        """Say it in `for_operator`'s thread, not the caller's.

        The two differ whenever something happens on an operator's behalf, and
        a message in the wrong conversation is worse than none: the operator
        never sees it, and somebody else sees work they did not do.

        **A question is the assistant speaking; an announcement is not.**
        `SYSTEM` is this door's default and the right one for what it was built
        to say -- a run finished, a skill was induced, things that HAPPENED
        rather than things anybody said. A question is the other kind, and the
        difference is load-bearing rather than cosmetic: `pending_job` reads
        back "the last thing the ASSISTANT decided", so a question filed as
        SYSTEM is one nothing can find.

        Measured on the deployment 2026-09-18. Three questions stood in the
        thread reading `Customer Type takes 4 characters. What should it be?`,
        the operator typed a sentence, and it went past all three to the skill
        resolver, which answered `Nobody has demonstrated that`. Every question
        this door has ever asked was invisible to the reader that exists to
        answer it, including the run path's since `5a2d10b1`.
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
                    speaker=speaker,
                    text=text,
                    said_at=self._clock.now(),
                    decision=decision,
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
