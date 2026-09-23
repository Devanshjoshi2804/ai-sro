from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion


class PromoteSkill:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        version: int,
        to: PromotionStage,
        acknowledging_fixed_values: bool = False,
    ) -> SkillVersion:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            target = skill.version(version)
            target.promote(
                to,
                self._clock.now(),
                ctx.principal_id,
                acknowledging_fixed_values=acknowledging_fixed_values,
                from_where="console",
            )
            await uow.skills.save(skill)
            await uow.commit()
        return target
