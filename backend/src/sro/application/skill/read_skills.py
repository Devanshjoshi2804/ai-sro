from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import Skill


class ListSkills:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]:
        async with self._uow as uow:
            return await uow.skills.list_for_tenant(ctx.tenant_id, limit=limit, offset=offset)


class GetSkill:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, skill_id: SkillId) -> Skill:
        async with self._uow as uow:
            return await uow.skills.get(ctx.tenant_id, skill_id)
