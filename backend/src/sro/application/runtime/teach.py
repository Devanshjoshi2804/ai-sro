from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.context import RequestContext
from sro.application.observation.chores import decide_sign_ins
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.belts import confirming_read, expected_statuses
from sro.domain.execution.compose import Adding, Composed, with_field, with_slots, without_slots
from sro.domain.execution.evidence import recorded_call
from sro.domain.execution.lanes import Broken, Lane, StepResult, accepts, cites_key, same_call
from sro.domain.execution.learned_step import K_NAME, LearnedStep
from sro.domain.execution.verified_writes import learned_pattern
from sro.domain.execution.write_plan import learned_slots
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import NotFound
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow


class Teach:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def learn(
        self,
        ctx: RequestContext,
        workflow: Workflow,
        by_id: Mapping[str, Gesture],
        step: Step,
        tried: Sequence[StepResult],
        *,
        run_id: str,
        values: Mapping[str, str],
    ) -> None:
        now = self._clock.now()
        won = tried[-1] if tried and tried[-1].verdict in ("done", "read") else None
        async with self._uow as uow:
            job = await _still(uow, ctx, workflow)
            if job is None:
                return
            for result in tried:
                if result.verdict == "failed" and result.fingerprint and not result.expired:
                    await uow.workflows.break_lane(
                        ctx.tenant_id,
                        workflow.id,
                        Broken(step.order, result.lane, result.fingerprint),
                        cites=cites_key(step),
                        at=now,
                    )
            slots = learned_slots(job, step)
            api_broke = any(
                one.lane is Lane.API
                and one.verdict == "failed"
                and one.fingerprint
                and not one.expired
                for one in tried
            )
            grown = (
                without_slots(job, slots)
                if api_broke and slots
                else with_slots(job, won.keyed)
                if won is not None
                and won.lane in (Lane.UI, Lane.SIGHT)
                and won.verdict == "done"
                and won.keyed
                else None
            )
            if grown is not None:
                await uow.workflows.save(grown)
            if won is not None:
                await uow.workflows.mend_lane(ctx.tenant_id, workflow.id, step.order, won.lane)
            if (
                won is not None
                and won.lane is Lane.SIGHT
                and (locator := _sighted(step, won, values))
            ):
                await uow.workflows.remember_locator(workflow.id, locator, by_run=run_id)
                await uow.workflows.mend_lane(ctx.tenant_id, workflow.id, step.order, Lane.UI)
            recorded = recorded_call(step, by_id)
            if (
                won is not None
                and won.lane is Lane.UI
                and won.verdict == "done"
                and recorded is not None
                and confirming_read(step, by_id) is not None
            ):
                wanted = expected_statuses(step, by_id)
                own = next(
                    (
                        call
                        for call in won.calls
                        if accepts(call.status, wanted)
                        and same_call(call, recorded, Adding()) is not None
                    ),
                    None,
                )
                pattern = None if own is None else learned_pattern(own.url, values, recorded.url)
                if own is not None and pattern is not None:
                    await uow.workflows.remember_write(
                        ctx.tenant_id,
                        method=own.method.upper(),
                        path_pattern=pattern,
                        origin=origin_of(own.url),
                        run_id=run_id,
                        workflow_id=workflow.id,
                        verified_by="status",
                        at=now.isoformat(),
                    )
            await uow.commit()

    async def locators(self, ctx: RequestContext, workflow: Workflow) -> dict[int, LearnedStep]:
        async with self._uow as uow:
            if await _still(uow, ctx, workflow) is None:
                return {}
            return {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}

    async def learn_field(
        self,
        ctx: RequestContext,
        pinned: Workflow,
        field: Composed,
        *,
        key: str,
        value: str,
        learned: Mapping[str, str],
        lane: Lane,
        run_id: str,
    ) -> None:
        async with self._uow as uow:
            workflow = await _still(uow, ctx, pinned)
            if workflow is None or any(field.name in one.parameters for one in workflow.steps):
                return
            grown, moved = with_field(workflow, field, key=key, value=value)
            await uow.workflows.grew(grown, moved=moved)
            await decide_sign_ins(uow, ctx.tenant_id, [grown])
            strategy, query = learned.get("strategy", ""), learned.get("query", "")
            if (
                strategy
                and query
                and len(query) <= K_NAME
                and value.casefold() not in query.casefold()
            ):
                await uow.workflows.remember_locator(
                    workflow.id,
                    LearnedStep(
                        field.before,
                        strategy,
                        query,
                        "sight" if lane is Lane.SIGHT else "composed",
                        frame_path=learned.get("frame_path"),
                    ),
                    by_run=run_id,
                )
            await uow.commit()


async def _still(uow: UnitOfWork, ctx: RequestContext, workflow: Workflow) -> Workflow | None:
    try:
        job = await uow.workflows.get(ctx.tenant_id, workflow.id, lock=True)
    except NotFound:
        return None
    return job if job.steps == workflow.steps else None


def _sighted(step: Step, won: StepResult, values: Mapping[str, str]) -> LearnedStep | None:
    strategy, query = won.learned.get("strategy"), won.learned.get("query")
    frame_path = won.learned.get("frame_path")
    if not (strategy and query and frame_path is not None) or len(query) > K_NAME:
        return None
    if any(
        value.strip().casefold() in query.casefold() for value in values.values() if value.strip()
    ):
        return None
    return LearnedStep(step.order, strategy, query, "sight", frame_path=frame_path)
