from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import SkillVersion


class DescribeSkill:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        version: int,
        summary: str,
        when_to_use: str,
    ) -> SkillVersion:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            target = skill.version(version)
            target.describe(summary=summary, when_to_use=when_to_use)
            await uow.skills.save(skill)
            await uow.commit()
        return target
