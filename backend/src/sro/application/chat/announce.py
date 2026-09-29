from __future__ import annotations

from sro.application.chat.converse import StartThread
from sro.application.chat.mailbox import K_ELSEWHERE, elsewhere_key
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Speaker, Thread, ThreadId, asking_about
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
        about: str = "",
    ) -> None:
        owner = RequestContext(ctx.tenant_id, for_operator)
        found = await self._thread_for(owner, about=about, run_id=str(decision.get("run_id") or ""))
        async with self._uow as uow:
            await self._say(uow, owner, found, text=text, decision=decision, speaker=speaker)
            await uow.commit()

    async def answered_elsewhere(self, ctx: RequestContext, run: WorkflowRun) -> None:
        asked = Progress.of(run.progress).asking
        if not asked.get("id") or asked.get("answered"):
            return
        owner = RequestContext(
            ctx.tenant_id, PrincipalId(run.started_by) if run.started_by else ctx.principal_id
        )
        found = await self._thread_for(owner, run_id=run.id)
        async with self._uow as uow:
            if not await uow.tool_calls.forget(
                ctx.tenant_id, elsewhere_key(run.id, asked["id"]), tool=K_ELSEWHERE
            ):
                return
            await self._say(
                uow,
                owner,
                found,
                text=(
                    "An answer to this run's question arrived in a mailbox you cannot read, "
                    "so it was never taken; the run stopped waiting for it."
                ),
                speaker=Speaker.ASSISTANT,
                decision={"kind": "note", "run_id": run.id},
            )
            await uow.commit()

    async def _thread_for(
        self, owner: RequestContext, *, about: str = "", run_id: str = ""
    ) -> ThreadId:
        if about.strip():
            opened = Thread(
                id=asking_about(owner.tenant_id, owner.principal_id, about),
                tenant_id=owner.tenant_id,
                opened_by=owner.principal_id,
                opened_at=self._clock.now(),
            )
            async with self._uow as uow:
                await uow.threads.open(opened)
                await uow.commit()
            return opened.id
        if run_id:
            async with self._uow as uow:
                named = await uow.threads.naming(
                    owner.tenant_id, opened_by=owner.principal_id, run_id=run_id
                )
            if named is not None:
                return named.id
        found = await ReadThreads(self._uow).current(owner) or await StartThread(
            self._uow, self._clock, self._ids
        ).execute(owner)
        return found.id

    async def _say(
        self,
        uow: UnitOfWork,
        owner: RequestContext,
        thread_id: ThreadId,
        *,
        text: str,
        decision: dict[str, object],
        speaker: Speaker,
    ) -> None:
        thread = await uow.threads.get(owner.tenant_id, thread_id)
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
