from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecutionRequest,
    NotRunnable,
    ensure_runnable,
)
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Medium, Run
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage


class RunFromPreview:
    def __init__(self, uow: UnitOfWork, clock: Clock, execute_skill: ExecuteSkill) -> None:
        self._uow = uow
        self._clock = clock
        self._execute = execute_skill

    async def begin(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        intent: str,
        previewed: int,
    ) -> Run:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            current = skill.runnable or skill.latest
            if current.version != previewed:
                raise NotRunnable(
                    "what you read is no longer what this task would do -- it has been "
                    "changed since you looked at it. Ask again and read it through before "
                    "it runs"
                )
            version = current
            now = self._clock.now()
            promoted = False
            while version.stage.rung < PromotionStage.ASSISTED.rung:
                version.promote(
                    version.stage.next_stage(),
                    now,
                    ctx.principal_id,
                    acknowledging_fixed_values=True,
                    from_where="preview",
                )
                promoted = True

            request = ExecutionRequest(
                skill_id=skill_id,
                parameters=parameters,
                version=version.version,
                authorized_by=str(ctx.principal_id),
                device_id=device_id,
                intent=intent,
                medium=Medium.UI,
                may_take_focus=True,
            )

            await ensure_runnable(uow, ctx, skill, version, request, now)

            if promoted:
                await uow.skills.save(skill)
                await uow.commit()

        return await self._execute.begin(ctx, request)
