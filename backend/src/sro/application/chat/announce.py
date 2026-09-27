from __future__ import annotations

from sro.application.chat.converse import StartThread
from sro.application.chat.mailbox import elsewhere_key
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Speaker
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.identifiers import PrincipalId


class SayWhatHappened:
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

    async def answered_elsewhere(self, ctx: RequestContext, run: WorkflowRun) -> None:
        asked = Progress.of(run.progress).asking
        if not asked.get("id") or asked.get("answered"):
            return
        async with self._uow as uow:
            if not await uow.tool_calls.forget(ctx.tenant_id, elsewhere_key(run.id, asked["id"])):
                return
            await self.execute(
                ctx,
                for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
                text=(
                    "An answer to this run's question arrived in a mailbox you cannot read, "
                    "so it was never taken; the run stopped waiting for it."
                ),
                speaker=Speaker.ASSISTANT,
                decision={"kind": "note", "run_id": run.id},
            )
