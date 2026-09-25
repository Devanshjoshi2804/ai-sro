from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, replace

from sro.application.context import RequestContext
from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.step import Held, LaneContext, NeedsAPerson, ReadsBack, Stopped
from sro.application.runtime.teach import Teach
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.account import Account
from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.execution.lanes import Lane, StepResult, cites_key
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.progress import MAIN, Progress
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow, cited_ids

_RUN_VERDICT = {"done": "held", "read": "held", "failed": "failed", "unknown": "unclear"}
_KEPT = ("held", "withheld")


@dataclass(frozen=True, slots=True)
class Prepared:
    browser: bool


@dataclass(frozen=True, slots=True)
class StepOutcome:
    more: bool
    asking: str = ""
    failed: bool = False


class RunSteps:
    def __init__(
        self,
        uow: UnitOfWork,
        broker: SessionBroker,
        executor: StepExecutor,
        teach: Teach,
        api: ReadsBack,
        clock: Clock,
    ) -> None:
        self._uow, self._broker, self._executor = uow, broker, executor
        self._teach, self._api, self._clock = teach, api, clock

    async def prepare(self, ctx: RequestContext, run_id: str) -> Prepared:
        run, workflow, by_id = await self._load(ctx, run_id)
        browser = [
            one
            for one in _ordered(workflow)
            if not sends_mail(one, by_id) and not only_reads_the_mail(one, by_id)
        ]
        progress = Progress.of(run.progress)
        if browser and not progress.start_url:
            first = primary_gesture(browser[0], by_id)
            progress.start_url = (first.page_url or first.url or "") if first else ""
            account = await self._broker.account_for(ctx, progress.start_url)
            progress.account.origin, progress.account.username = account.origin, account.username
            await self._record(ctx, run_id, progress)
        return Prepared(browser=bool(browser))

    async def acquire(self, ctx: RequestContext, run_id: str) -> None:
        progress = Progress.of((await self._run(ctx, run_id)).progress)
        if progress.lease and progress.tabs.get(MAIN):
            with contextlib.suppress(PageGone):
                await self._broker.reattach(ctx, progress.lease, progress.tabs[MAIN])
                return
        account = Account.of(
            ctx.tenant_id.value, progress.account.origin, progress.account.username
        )
        held = await self._broker.acquire(ctx, account, progress.start_url, holder=run_id)
        progress.lease, progress.tabs = held.lease.id, {MAIN: held.target_id}
        await self._record(ctx, run_id, progress)

    async def step(self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event) -> StepOutcome:
        run, workflow, by_id = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        ordered = _ordered(workflow)
        if progress.step >= len(ordered):
            return StepOutcome(more=False)
        step = ordered[progress.step]
        values = {**run.values, **progress.read}
        if progress.written(step.order):
            done = StepResult("done", Lane.UI, "already done")
            by = progress.marks[step.order].lane
            return await self._advance(ctx, run, progress, step, ordered, done, by=by)
        if not run.live and writes(step, by_id):
            withheld = StepResult("read", Lane.UI, "a dry run: withheld")
            return await self._advance(ctx, run, progress, step, ordered, withheld, withheld=True)
        tried: tuple[StepResult, ...] = ()
        try:
            held = await self._held(ctx, run_id, progress)
            lane = await self._lane_context(ctx, run, workflow, by_id, held, stop, step)
            if progress.in_doubt(step.order):
                lost = StepResult("unknown", Lane.API, "sent by an earlier attempt, never settled")
                return await self._settled(ctx, run, progress, step, ordered, values, lane, lost)
            async with self._uow as uow:
                broken = await uow.workflows.broken_for(
                    ctx.tenant_id, workflow.id, {one.order: cites_key(one) for one in ordered}
                )
            tried = await self._executor.run(
                step, values, lane, broken=broken, start_url=progress.start_url
            )
        except Stopped:
            return await self._stopped(ctx, run_id, step)
        except (NeedsAPerson, AccountBusy, PageGone) as why:
            if why.tried:
                await self._teach.learn(
                    ctx, workflow, by_id, step, why.tried, run_id=run_id, values=values
                )
            if isinstance(why, NeedsAPerson):
                return await self._ask(ctx, run_id, step, why)
            raise
        await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)
        run = await self._run(ctx, run_id)
        progress = Progress.of(run.progress)
        last = tried[-1] if tried else StepResult("failed", Lane.UI, "no lane could act on it")
        if last.verdict == "unknown":
            return await self._settled(ctx, run, progress, step, ordered, values, lane, last)
        if last.verdict == "failed":
            asked = NeedsAPerson(f"'{step.says}' could not be done: {last.reason}", kind="step")
            return await self._ask(ctx, run_id, step, asked, last=last)
        return await self._advance(ctx, run, progress, step, ordered, last)

    async def finish(self, ctx: RequestContext, run_id: str) -> str:
        run, workflow, _ = await self._load(ctx, run_id)
        if run.outcome == "running":
            done = Progress.of(run.progress).step >= len(workflow.steps)
            kept = done and all(one.verdict in _KEPT for one in run.steps)
            run.outcome = "held" if kept else "failed"
        run.finished_at = run.finished_at or self._clock.now().isoformat()
        async with self._uow as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()
        return run.outcome

    async def release(self, ctx: RequestContext, run_id: str) -> None:
        progress = Progress.of((await self._run(ctx, run_id)).progress)
        if not progress.tabs.get(MAIN):
            return
        with contextlib.suppress(PageGone):
            held = await self._broker.reattach(ctx, progress.lease, progress.tabs[MAIN])
            await self._broker.release(ctx, held)
        progress.tabs = {}
        await self._record(ctx, run_id, progress)

    async def beat(self, ctx: RequestContext, run_id: str) -> None:
        progress = Progress.of((await self._run(ctx, run_id)).progress)
        if progress.lease:
            await self._broker.beat(ctx, progress.lease, holder=run_id)

    async def _held(self, ctx: RequestContext, run_id: str, progress: Progress) -> Held | None:
        tab = progress.tabs.get(MAIN)
        if not tab:
            return None
        try:
            return await self._broker.reattach(ctx, progress.lease, tab)
        except PageGone:
            held = await self._broker.recover(
                ctx, progress.lease, progress.start_url, holder=run_id
            )
        progress.lease, progress.tabs = held.lease.id, {MAIN: held.target_id}
        await self._record(ctx, run_id, progress)
        return held

    async def _lane_context(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        workflow: Workflow,
        by_id: dict[str, Gesture],
        held: Held | None,
        stop: asyncio.Event,
        step: Step,
    ) -> LaneContext:
        async with self._uow as uow:
            learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}
            ledger = await uow.workflows.learned_writes(ctx.tenant_id)
        waiting = read_wait(run.awaiting)

        async def about_to_write() -> None:
            await self._sending(ctx, run.id, step.order)

        return LaneContext(
            tenant_id=ctx.tenant_id,
            principal_id=ctx.principal_id,
            workflow=workflow,
            by_id=by_id,
            learned=learned,
            ledger=ledger,
            held=held,
            stop=stop,
            thread=waiting.thread if waiting else "",
            about_to_write=about_to_write,
        )

    async def _sending(self, ctx: RequestContext, run_id: str, order: int) -> None:
        progress = Progress.of((await self._run(ctx, run_id)).progress)
        progress.sending(order)
        await self._record(ctx, run_id, progress)

    async def _settled(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        step: Step,
        ordered: list[Step],
        values: dict[str, str],
        lane: LaneContext,
        lost: StepResult,
    ) -> StepOutcome:
        verdict = await self._api.read_back(step, values, replace(lane, reauthed=lost.expired))
        if verdict is None:
            asked = NeedsAPerson(
                f"'{step.says}' was sent and nothing confirms it; check it and answer",
                kind="step",
            )
            return await self._ask(ctx, run.id, step, asked, last=lost)
        settled = replace(lost, verdict=verdict, reason="settled by a read-back")
        return await self._advance(ctx, run, progress, step, ordered, settled)

    async def _advance(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        step: Step,
        ordered: list[Step],
        result: StepResult,
        *,
        by: str = "",
        withheld: bool = False,
    ) -> StepOutcome:
        by = by or result.lane.value
        progress.settle(step.order, lane=by, verdict=result.verdict, never_left=result.never_left)
        progress.read.update(result.read)
        progress.step += 1
        run.steps.append(
            RunStep(
                order=len(run.steps),
                of_step=step.order,
                says=step.says,
                verdict="withheld" if withheld else _RUN_VERDICT[result.verdict],
                verdict_by=by,
                planned_by=by,
                reason=result.reason,
                made=dict(result.read),
            )
        )
        async with self._uow as uow:
            if not await uow.workflow_runs.record_progress(
                ctx.tenant_id, run.id, progress.as_json()
            ):
                raise Stopped(f"run {run.id} is not known")
            await uow.workflow_runs.save(run)
            await uow.commit()
        return StepOutcome(more=progress.step < len(ordered))

    async def _ask(
        self,
        ctx: RequestContext,
        run_id: str,
        step: Step,
        asked: NeedsAPerson,
        *,
        last: StepResult | None = None,
    ) -> StepOutcome:
        run = await self._run(ctx, run_id)
        progress = Progress.of(run.progress)
        if last is not None:
            progress.settle(
                step.order, lane=last.lane.value, verdict=last.verdict, never_left=last.never_left
            )
        asking = f"q-{run_id}-{step.order}-{len(run.steps)}"
        progress.asking = {"id": asking, "kind": asked.kind, "text": asked.question}
        await self._record(ctx, run_id, progress)
        return StepOutcome(more=True, asking=asking)

    async def _stopped(self, ctx: RequestContext, run_id: str, step: Step) -> StepOutcome:
        run = await self._run(ctx, run_id)
        doubt = Progress.of(run.progress).in_doubt(step.order)
        run.outcome = "aborted"
        run.steps.append(
            RunStep(
                order=len(run.steps),
                of_step=step.order,
                says=step.says,
                verdict="unclear" if doubt else "skipped",
                verdict_by="none",
                reason="stopped by the operator",
            )
        )
        async with self._uow as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()
        return StepOutcome(more=False, failed=True)

    async def _record(self, ctx: RequestContext, run_id: str, progress: Progress) -> None:
        async with self._uow as uow:
            if not await uow.workflow_runs.record_progress(
                ctx.tenant_id, run_id, progress.as_json()
            ):
                raise Stopped(f"run {run_id} is not known")
            await uow.commit()

    async def _run(self, ctx: RequestContext, run_id: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise Stopped(f"run {run_id} is not known")
        return run

    async def _load(
        self, ctx: RequestContext, run_id: str
    ) -> tuple[WorkflowRun, Workflow, dict[str, Gesture]]:
        run = await self._run(ctx, run_id)
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow)))
            )
        return run, workflow, {one.id: one for one in cited}


def _ordered(workflow: Workflow) -> list[Step]:
    return sorted(workflow.steps, key=lambda one: one.order)
