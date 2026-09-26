from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.fill_field import Filled, FillField
from sro.application.runtime.step import (
    Held,
    LaneContext,
    NeedsAPerson,
    ReadsBack,
    Stopped,
    Superseded,
    WaitingForAPerson,
)
from sro.application.runtime.teach import Teach
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.chat.thread import Speaker
from sro.domain.execution.account import Account, LeaseState
from sro.domain.execution.compose import Adding, Composed, choices, compose, field_of
from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.execution.lanes import Lane, StepResult, cites_key
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.progress import MAIN, Progress, StepMark
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.learned import demanded
from sro.domain.skill.workflow import Step, Workflow, cited_ids, field_key

_RUN_VERDICT = {"done": "held", "read": "held", "failed": "failed", "unknown": "unclear"}
_KEPT = ("held", "withheld", "skipped")


@dataclass(frozen=True, slots=True)
class Prepared:
    browser: bool
    asking: str = ""


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
        ids: IdFactory,
        *,
        fill: FillField,
    ) -> None:
        self._uow, self._broker, self._executor = uow, broker, executor
        self._teach, self._api, self._clock, self._ids = teach, api, clock, ids
        self._fill = fill

    async def prepare(self, ctx: RequestContext, run_id: str) -> Prepared:
        run, workflow, by_id = await self._load(ctx, run_id)
        if run.outcome != "running":
            return Prepared(browser=False)
        ordered = _ordered(workflow)
        browser = [
            one
            for one in ordered
            if not sends_mail(one, by_id)
            and not only_reads_the_mail(one, by_id)
            and primary_gesture(one, by_id) is not None
        ]
        progress = Progress.of(run.progress)
        known = {one.get("name") for one in progress.composed}
        fresh = [_entry(one) for one in compose(workflow, by_id, run.values)[0]]
        if fresh := [one for one in fresh if one["name"] not in known]:
            progress.composed += fresh
            await self._write(ctx, run, progress)
        if browser and not progress.start_url:
            first = primary_gesture(browser[0], by_id)
            progress.start_url = (first.page_url or first.url or "") if first else ""
            try:
                account = await self._broker.account_for(ctx, progress.start_url)
            except NeedsAPerson as asked:
                asking = await self._ask(ctx, run, _standing(ordered, progress), asked)
                return Prepared(browser=True, asking=asking)
            progress.account.origin, progress.account.username = account.origin, account.username
            await self._write(ctx, run, progress)
        return Prepared(browser=bool(browser))

    async def acquire(
        self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event | None = None
    ) -> str:
        asking = await self._acquire(ctx, run_id)
        if stop is not None and stop.is_set():
            await self.stopped(ctx, run_id)
        return asking

    async def step(self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event) -> StepOutcome:
        run, workflow, by_id = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        ordered = _ordered(workflow)
        index = progress.step
        if run.outcome != "running" or index >= len(ordered):
            return StepOutcome(more=False)
        step = ordered[index]
        values = {**run.values, **progress.read}
        if progress.written(step.order):
            done = StepResult("done", Lane.UI, "already done")
            by = progress.marks[step.order].lane
            return await self._advance(ctx, run, progress, step, ordered, index, done, by=by)
        if index == 0:
            placing = {one.get("name") for one in progress.composed}
            unplaced = [
                one for one in compose(workflow, by_id, run.values)[1] if one.name not in placing
            ]
            if unplaced:
                one = unplaced[0]
                asked = NeedsAPerson(
                    f"'{one.name}' matches "
                    + ("more than one field" if one.why == "ambiguous" else "no field")
                    + " on the form; "
                    + _choose(one.labels),
                    kind="field",
                )
                return StepOutcome(
                    more=True,
                    asking=await self._ask(
                        ctx, run, step, asked, index=index, about=(one.name, one.why, one.labels)
                    ),
                )
        absent = [name for name in step.parameters if not values.get(name, "").strip()]
        required = [name for name in absent if name in _demanded(workflow)]
        if required:
            asked = NeedsAPerson(
                f"'{step.says}' needs a value for {', '.join(required)} and none was given",
                kind="value",
            )
            return StepOutcome(
                more=True, asking=await self._ask(ctx, run, step, asked, index=index)
            )
        if absent and len(absent) == len(step.parameters):
            left_out = StepResult("read", Lane.UI, f"no value was given for {', '.join(absent)}")
            return await self._advance(
                ctx, run, progress, step, ordered, index, left_out, verdict="skipped"
            )
        if not run.live and writes(step, by_id):
            withheld = StepResult("read", Lane.UI, "a dry run: withheld")
            return await self._advance(
                ctx, run, progress, step, ordered, index, withheld, verdict="withheld"
            )
        tried: tuple[StepResult, ...] = ()
        try:
            held = await self._held(ctx, run, progress)
            lane = await self._lane_context(ctx, run, workflow, by_id, held, stop, step)
            if field_key(workflow, step):
                return await self._fill_step(ctx, run, progress, ordered, index, values, lane)
            if progress.in_doubt(step.order):
                mark = progress.marks[step.order]
                lost = StepResult(
                    "unknown",
                    _lane_of(mark.lane),
                    "sent by an earlier attempt, never settled",
                    expired=mark.expired,
                )
                return await self._settled(
                    ctx, run, progress, step, ordered, index, values, lane, lost
                )
            async with self._uow as uow:
                broken = await uow.workflows.broken_for(
                    ctx.tenant_id, workflow.id, {one.order: cites_key(one) for one in ordered}
                )
            adding, stopped = await self._fill_for(ctx, run, progress, ordered, index, values, lane)
            if stopped is not None:
                return stopped
            if adding is not None:
                lane = replace(lane, adding={step.order: adding})
            tried = await self._executor.run(
                step, values, lane, broken=broken, start_url=progress.start_url
            )
        except Superseded:
            raise
        except Stopped:
            return await self._stopped(ctx, run_id, step)
        except (NeedsAPerson, AccountBusy, PageGone) as why:
            if why.tried:
                await self._teach.learn(
                    ctx, workflow, by_id, step, why.tried, run_id=run_id, values=values
                )
            if isinstance(why, NeedsAPerson):
                last = why.tried[-1] if why.tried else None
                run = await self._run(ctx, run_id)
                return StepOutcome(
                    more=True, asking=await self._ask(ctx, run, step, why, last=last, index=index)
                )
            raise
        run = await self._run(ctx, run_id)
        progress = Progress.of(run.progress)
        last = tried[-1] if tried else StepResult("failed", Lane.UI, "no lane could act on it")
        if lane.adding:
            earlier = _fields_for(workflow, ordered, index, progress.filled)
            _settle_fields(run, progress, step, earlier, last)
            await self._write(ctx, run, progress, save=True, index=index)
        if last.verdict == "unknown":
            outcome = await self._settled(
                ctx, run, progress, step, ordered, index, values, lane, last
            )
        elif last.verdict == "failed":
            asked = NeedsAPerson(f"'{step.says}' could not be done: {last.reason}", kind="step")
            outcome = StepOutcome(
                more=True, asking=await self._ask(ctx, run, step, asked, last=last, index=index)
            )
        else:
            outcome = await self._advance(ctx, run, progress, step, ordered, index, last)
        await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)
        return outcome

    async def finish(self, ctx: RequestContext, run_id: str) -> str:
        run, workflow, _ = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        confirmed = [one for one in progress.composed if one.get("verdict") == "done"]
        for one in sorted(confirmed, key=lambda one: int(str(one["before"])), reverse=True):
            learned = one.get("learned")
            await self._teach.learn_field(
                ctx,
                workflow.id,
                _composed(one),
                key=str(one["key"]),
                value=run.values.get(str(one["name"]), ""),
                learned=_strings(learned),
                lane=_lane_of(str(one.get("lane") or "")),
                run_id=run.id,
            )
        if run.outcome == "running":
            last = {one.of_step: one.verdict for one in sorted(run.steps, key=lambda s: s.order)}
            done = progress.step >= len(workflow.steps)
            kept = (
                done
                and all(verdict in _KEPT for verdict in last.values())
                and len(confirmed) == len(progress.composed)
            )
            run.outcome = "held" if kept else "failed"
        if not run.needs:
            run.awaiting = None
        run.finished_at = run.finished_at or self._clock.now().isoformat()
        async with self._uow as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()
        return run.outcome

    async def stopped(self, ctx: RequestContext, run_id: str) -> None:
        run = await self._run(ctx, run_id)
        if run.outcome != "running":
            return
        run.outcome = "aborted"
        async with self._uow as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

    async def release(self, ctx: RequestContext, run_id: str) -> None:
        run = await self._run(ctx, run_id)
        progress = Progress.of(run.progress)
        waits = progress.asking.get("kind", "")
        if run.outcome == "running" and waits == "code":
            return
        if progress.tabs.get(MAIN):
            with contextlib.suppress(PageGone):
                held = await self._broker.reattach(
                    ctx, progress.lease, progress.tabs[MAIN], holder=run.id
                )
                await self._broker.release(ctx, held)
            progress.tabs = {}
            await self._write(ctx, run, progress)
        if run.outcome != "running" and progress.lease:
            async with self._uow as uow:
                lease = await uow.browser_sessions.get_lease(ctx.tenant_id, progress.lease)
            if lease is not None and lease.state is LeaseState.WAITING and lease.holder == run.id:
                await self._broker.unpark(ctx, lease.id, lease.waits_for)

    async def answered(self, ctx: RequestContext, run_id: str, question_id: str) -> None:
        run, workflow, by_id = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        asking = progress.asking
        if asking.get("id") != question_id or not asking.get("answered"):
            return
        kind, verdict = asking.get("kind"), asking.get("verdict", "")
        if kind == "password" and progress.lease:
            await self._broker.unpark(ctx, progress.lease, "password")
        progress.asking = {}
        if kind == "field":
            name, choice = asking.get("name", ""), asking.get("choice", "")
            others = [one for one in progress.composed if one.get("name") != name]
            if not choice:
                run.values.pop(name, None)
                run.unasked = [*(one for one in run.unasked if one != name), name]
                progress.composed = others
            elif asking.get("why") == "no_option":
                run.values[name] = choice
            elif asking.get("why") == "failed":
                pass
            elif (hit := choices(workflow, by_id).get(choice)) is not None:
                progress.composed = [*others, _entry(replace(hit, name=name))]
        if kind == "step" and verdict:
            ordered = _ordered(workflow)
            index = progress.step
            step = ordered[index]
            if verdict == "done":
                said = StepResult("done", Lane.UI, "the operator says it was done")
                await self._advance(ctx, run, progress, step, ordered, index, said, by="operator")
                return
            mark = progress.marks.get(step.order, StepMark())
            progress.settle(step.order, lane=mark.lane, verdict="failed", never_left=True)
            run.steps.append(
                RunStep(
                    order=len(run.steps),
                    of_step=step.order,
                    says=step.says,
                    verdict="failed",
                    verdict_by="operator",
                    planned_by="operator",
                    reason="the operator says it was not done; it is tried again",
                )
            )
        await self._write(ctx, run, progress, save=True)

    async def beat(self, ctx: RequestContext, run_id: str) -> None:
        progress = Progress.of((await self._run(ctx, run_id)).progress)
        if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):
            raise PageGone(f"lease {progress.lease} is no longer live")

    async def _acquire(self, ctx: RequestContext, run_id: str) -> str:
        run, workflow, _ = await self._load(ctx, run_id)
        if run.outcome != "running":
            return ""
        progress = Progress.of(run.progress)
        try:
            if progress.lease and progress.tabs.get(MAIN):
                with contextlib.suppress(PageGone):
                    kept = await self._broker.reattach(
                        ctx, progress.lease, progress.tabs[MAIN], holder=run.id
                    )
                    if kept.lease.state is not LeaseState.WAITING:
                        return ""
                    held = await self._broker.resume(
                        ctx, kept.lease.id, kept.target_id, progress.start_url, holder=run_id
                    )
                    await self._keep_tab(ctx, run, progress, held)
                    return ""
            account = Account.of(
                ctx.tenant_id.value, progress.account.origin, progress.account.username
            )
            held = await self._broker.acquire(ctx, account, progress.start_url, holder=run_id)
        except NeedsAPerson as asked:
            return await self._ask(ctx, run, _standing(_ordered(workflow), progress), asked)
        await self._keep_tab(ctx, run, progress, held)
        return ""

    async def _held(self, ctx: RequestContext, run: WorkflowRun, progress: Progress) -> Held | None:
        tab = progress.tabs.get(MAIN)
        if not tab:
            return None
        try:
            return await self._broker.reattach(ctx, progress.lease, tab, holder=run.id)
        except PageGone:
            held = await self._broker.recover(
                ctx, progress.lease, progress.start_url, holder=run.id
            )
        await self._keep_tab(ctx, run, progress, held)
        return held

    async def _keep_tab(
        self, ctx: RequestContext, run: WorkflowRun, progress: Progress, held: Held
    ) -> None:
        progress.lease, progress.tabs = held.lease.id, {MAIN: held.target_id}
        try:
            await self._write(ctx, run, progress)
        except BaseException:
            await self._broker.release(ctx, held)
            raise

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
        marked: list[Lane] = []

        async def about_to_write(lane: Lane) -> None:
            await self._sending(ctx, run.id, step.order, lane, again=bool(marked))
            marked.append(lane)

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

    async def _sending(
        self, ctx: RequestContext, run_id: str, order: int, lane: Lane, *, again: bool
    ) -> None:
        run = await self._run(ctx, run_id)
        progress = Progress.of(run.progress)
        wrote = progress.marks.get(order, StepMark()).wrote
        if again and wrote == "sending":
            return
        if wrote:
            raise Superseded(f"step {order} of {run_id} is already {wrote} by another attempt")
        progress.sending(order, lane.value)
        await self._write(ctx, run, progress)

    async def _settled(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        step: Step,
        ordered: list[Step],
        index: int,
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
            return StepOutcome(
                more=True, asking=await self._ask(ctx, run, step, asked, last=lost, index=index)
            )
        settled = replace(lost, verdict=verdict, reason="settled by a read-back")
        return await self._advance(ctx, run, progress, step, ordered, index, settled)

    async def _advance(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        step: Step,
        ordered: list[Step],
        index: int,
        result: StepResult,
        *,
        by: str = "",
        verdict: str = "",
    ) -> StepOutcome:
        by = by or result.lane.value
        progress.settle(
            step.order,
            lane=by,
            verdict=result.verdict,
            never_left=result.never_left,
            expired=result.expired,
        )
        progress.read.update(result.read)
        progress.step, progress.asking = index + 1, {}
        run.steps.append(
            RunStep(
                order=len(run.steps),
                of_step=step.order,
                says=step.says,
                verdict=verdict or _RUN_VERDICT[result.verdict],
                verdict_by=by,
                planned_by=by,
                reason=result.reason,
                made=dict(result.read),
            )
        )
        await self._write(ctx, run, progress, save=True, index=index)
        return StepOutcome(more=progress.step < len(ordered))

    async def _ask(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        step: Step,
        asked: NeedsAPerson,
        *,
        last: StepResult | None = None,
        index: int | None = None,
        about: tuple[str, str, Sequence[str]] | None = None,
    ) -> str:
        progress = Progress.of(run.progress)
        if last is not None:
            progress.settle(
                step.order,
                lane=last.lane.value,
                verdict=last.verdict,
                never_left=last.never_left,
                expired=last.expired,
            )
        if isinstance(asked, WaitingForAPerson):
            progress.lease, progress.tabs = asked.held.lease.id, {MAIN: asked.held.target_id}
        asking = f"q_{secrets.token_hex(16)}"
        progress.asking = {
            "id": asking,
            "kind": asked.kind,
            "text": asked.question,
            "step": str(step.order),
        }
        if about is not None:
            name, why, choices = about
            progress.asking |= {"name": name, "why": why, "choices": json.dumps(list(choices))}
        by = last.lane.value if last is not None else "none"
        run.steps.append(
            RunStep(
                order=len(run.steps),
                of_step=step.order,
                says=step.says,
                verdict="unclear" if last is not None and last.verdict == "unknown" else "failed",
                verdict_by=by,
                planned_by=by,
                reason=asked.question,
            )
        )
        await self._write(ctx, run, progress, save=True, index=index, open_step=step.order)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
            text=asked.question,
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": "run_asks",
                "run_id": run.id,
                "question_id": asking,
                "asks": asked.kind,
                **({} if about is None else {"name": about[0], "choices": list(about[2])}),
            },
        )
        return asking

    async def _fill_for(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        ordered: list[Step],
        index: int,
        values: dict[str, str],
        lane: LaneContext,
    ) -> tuple[Adding | None, StepOutcome | None]:
        step = ordered[index]
        earlier = _fields_for(lane.workflow, ordered, index, progress.filled)
        known = {field_key(lane.workflow, one): one.parameters[0] for one in earlier}
        if any(row.of_step == step.order for row in run.steps):
            for before in earlier:
                field = field_of(lane.workflow, lane.by_id, before)
                name = before.parameters[0]
                again = (
                    Filled(None, detail="the form its save shows has no such field any more")
                    if field is None
                    else await self._fill.fill(
                        field,
                        values.get(name, ""),
                        step,
                        lane,
                        learned=lane.learned.get(before.order),
                    )
                )
                if again.lane is None:
                    return None, await self._not_filled(
                        ctx,
                        run,
                        step,
                        index,
                        field or Composed(name, name, "", step.order),
                        again,
                        lane,
                    )
                progress.filled[name] = again.held
        fresh = {name: progress.filled[name] for name in known.values()}
        composing = [one for one in progress.composed if one.get("before") == step.order]
        for one in composing:
            field = _composed(one)
            filled = await self._fill.fill(field, values.get(field.name, ""), step, lane)
            if filled.lane is None:
                return None, await self._not_filled(ctx, run, step, index, field, filled, lane)
            one |= {
                "lane": filled.lane.value,
                "verdict": "unknown",
                "learned": dict(filled.learned),
            }
            fresh[field.name] = filled.held
        if not known and not composing:
            return None, None
        await self._write(ctx, run, progress, index=index)
        return Adding(known=known, fresh=fresh), None

    async def _not_filled(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        write: Step,
        index: int,
        field: Composed,
        filled: Filled,
        lane: LaneContext,
    ) -> StepOutcome:
        if filled.sent:
            await self._sending(ctx, run.id, write.order, Lane.SIGHT, again=False)
            return StepOutcome(more=True)
        asking = await self._fill_asks(ctx, run, write, index, field, filled, lane)
        return StepOutcome(more=True, asking=asking)

    async def _fill_step(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        ordered: list[Step],
        index: int,
        values: dict[str, str],
        lane: LaneContext,
    ) -> StepOutcome:
        step = ordered[index]
        name = step.parameters[0]
        field = field_of(lane.workflow, lane.by_id, step)
        write = None if field is None else _step_at(ordered, field.before)
        if write is not None and (progress.in_doubt(write.order) or progress.written(write.order)):
            mark = progress.marks[write.order]
            gone = StepResult("unknown", _lane_of(mark.lane), "its save was already sent")
            return await self._advance(ctx, run, progress, step, ordered, index, gone)
        if field is None or write is None:
            filled = Filled(None, detail="the form its save shows has no such field any more")
        else:
            filled = await self._fill.fill(
                field, values[name], write, lane, learned=lane.learned.get(step.order)
            )
        if filled.sent and write is not None:
            await self._sending(ctx, run.id, write.order, Lane.SIGHT, again=False)
            run = await self._run(ctx, run.id)
            said = StepResult("unknown", Lane.SIGHT, filled.detail)
            return await self._advance(
                ctx, run, Progress.of(run.progress), step, ordered, index, said
            )
        if filled.lane is None:
            label = step.says.removeprefix("Fill ")
            asking = await self._fill_asks(
                ctx, run, step, index, field or Composed(name, label, "", step.order), filled, lane
            )
            return StepOutcome(more=True, asking=asking)
        progress.filled[name] = filled.held
        sent = StepResult("unknown", filled.lane, "filled; only the save's own call confirms it")
        return await self._advance(ctx, run, progress, step, ordered, index, sent)

    async def _fill_asks(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        step: Step,
        index: int,
        field: Composed,
        filled: Filled,
        lane: LaneContext,
    ) -> str:
        about: tuple[str, str, Sequence[str]]
        if filled.options:
            many = "more than one option" if filled.asks == "ambiguous" else "no option"
            asked = NeedsAPerson(
                f"'{field.label}' has {many} like the value asked for; choose one, or leave it out",
                kind="field",
            )
            about = (field.name, "no_option", filled.options)
        elif filled.asks and not field_key(lane.workflow, step):
            same = (field.label, field.role, field.before)
            offered = [
                said
                for said, one in choices(lane.workflow, lane.by_id).items()
                if (one.label, one.role, one.before) != same
            ]
            asked = NeedsAPerson(
                f"the page shows {'more than one' if filled.asks == 'ambiguous' else 'no'} "
                f"field labelled '{field.label}'; " + _choose(offered),
                kind="field",
            )
            about = (field.name, filled.asks, offered)
        else:
            reason = filled.detail or f"the page has no single field labelled '{field.label}'"
            asked = NeedsAPerson(
                f"'Fill {field.label}' could not be done: {reason}; choose "
                f"'{field.label}' to try it again, or leave it out",
                kind="field",
            )
            about = (field.name, "failed", (field.label,))
        return await self._ask(ctx, run, step, asked, index=index, about=about)

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

    async def _write(
        self,
        ctx: RequestContext,
        run: WorkflowRun,
        progress: Progress,
        *,
        save: bool = False,
        index: int | None = None,
        open_step: int | None = None,
    ) -> None:
        loaded = Progress.of(run.progress)
        if (index is not None and loaded.step != index) or (
            open_step is not None and loaded.written(open_step)
        ):
            raise Superseded(f"{run.id} moved past this step under another attempt")
        now = progress.as_json()
        async with self._uow as uow:
            kept = await uow.workflow_runs.record_progress(
                ctx.tenant_id, run.id, now, was=run.progress
            )
            if kept:
                if save:
                    await uow.workflow_runs.save(run)
                await uow.commit()
        if not kept:
            await self._run(ctx, run.id)
            raise Superseded(f"{run.id} was moved on by another attempt")
        run.progress = now

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


def _demanded(workflow: Workflow) -> set[str]:
    return {
        str(parameter["name"])
        for parameter in workflow.parameters
        if parameter.get("name") and demanded(parameter)
    }


def _ordered(workflow: Workflow) -> list[Step]:
    return sorted(workflow.steps, key=lambda one: one.order)


def _standing(ordered: list[Step], progress: Progress) -> Step:
    return ordered[min(progress.step, len(ordered) - 1)]


def _entry(field: Composed) -> dict[str, object]:
    return {
        "name": field.name,
        "label": field.label,
        "role": field.role,
        "before": field.before,
        "options": None if field.options is None else list(field.options),
        "lane": "",
        "verdict": "",
        "key": "",
    }


def _composed(entry: dict[str, object]) -> Composed:
    options = entry.get("options")
    return Composed(
        str(entry["name"]),
        str(entry["label"]),
        str(entry["role"]),
        int(str(entry["before"])),
        None if not isinstance(options, list) else tuple(str(one) for one in options),
    )


def _strings(value: object) -> dict[str, str]:
    return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _fields_for(
    workflow: Workflow, ordered: list[Step], index: int, filled: Mapping[str, str]
) -> list[Step]:
    found: list[Step] = []
    for one in reversed(ordered[:index]):
        if not field_key(workflow, one):
            break
        if one.parameters[0] in filled:
            found.append(one)
    return found


def _settle_fields(
    run: WorkflowRun, progress: Progress, step: Step, earlier: list[Step], last: StepResult
) -> None:
    keyed = last.keyed if last.verdict == "done" else {}
    for one in progress.composed:
        if one.get("before") != step.order or not one.get("lane"):
            continue
        name = str(one["name"])
        if name in keyed:
            one |= {"verdict": "done", "key": keyed[name]}
        elif last.verdict == "failed":
            one["verdict"] = "failed"
        elif last.verdict == "done":
            run.steps.append(
                RunStep(
                    order=len(run.steps),
                    of_step=step.order,
                    says=f"Fill {one['label']}",
                    verdict="unclear",
                    verdict_by=str(one["lane"]),
                    planned_by=str(one["lane"]),
                    reason="the save did not carry it",
                )
            )
    for field in earlier:
        name = field.parameters[0]
        verdict = "held" if name in keyed else "failed" if last.verdict == "failed" else ""
        if not verdict:
            continue
        by = progress.marks.get(field.order, StepMark()).lane or "none"
        run.steps.append(
            RunStep(
                order=len(run.steps),
                of_step=field.order,
                says=field.says,
                verdict=verdict,
                verdict_by=by,
                planned_by=by,
                reason="the save's own call carried it"
                if verdict == "held"
                else "the save it went with failed",
            )
        )


def _choose(offered: Sequence[str]) -> str:
    return (
        "choose the field it goes in, or leave it out"
        if offered
        else "the only answer is to leave it out"
    )


def _step_at(ordered: list[Step], order: int) -> Step | None:
    return next((one for one in ordered if one.order == order), None)


def _lane_of(value: str) -> Lane:
    return Lane(value) if value in {one.value for one in Lane} else Lane.API
