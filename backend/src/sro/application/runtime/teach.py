from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.ui_lane import same_call
from sro.domain.execution.belts import confirming_read, expected_statuses
from sro.domain.execution.compose import Adding
from sro.domain.execution.evidence import recorded_call
from sro.domain.execution.lanes import Broken, Lane, StepResult, accepts, cites_key
from sro.domain.execution.learned_step import K_NAME, LearnedStep
from sro.domain.execution.verified_writes import learned_pattern
from sro.domain.observation.gesture import Gesture
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
            for result in tried:
                if result.verdict == "failed" and result.fingerprint and not result.expired:
                    await uow.workflows.break_lane(
                        ctx.tenant_id,
                        workflow.id,
                        Broken(step.order, result.lane, result.fingerprint),
                        cites=cites_key(step),
                        at=now,
                    )
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
                    if not any(one.lane is Lane.API and one.verdict == "failed" for one in tried):
                        await uow.workflows.mend_lane(
                            ctx.tenant_id, workflow.id, step.order, Lane.API
                        )
            await uow.commit()


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
