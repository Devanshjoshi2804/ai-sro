"""Move a skill version one rung up the promotion ladder.

Thin by design: the rules live on ``PromotionStage`` so they hold on every path,
not only the ones that remember to call a service.
"""

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
        """Move one version up one rung.

        ``acknowledging_fixed_values`` is the supervisor answering the one
        refusal they are allowed to answer: a version induced from a single
        demonstration sends the same values every time, and above shadow those
        values are actually sent. Saying so is a decision with a name on it, not
        a flag to default to true.
        """
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            target = skill.version(version)
            target.promote(
                to,
                self._clock.now(),
                ctx.principal_id,
                acknowledging_fixed_values=acknowledging_fixed_values,
                # This is a person opening the console and looking at the
                # evidence, not a press on the panel's preview. The two are
                # both reviews, and a blank here would read as either -- an old
                # row from before this field existed, or this one -- which is
                # exactly the ambiguity ADR 014 exists to remove.
                from_where="console",
            )
            await uow.skills.save(skill)
            await uow.commit()
        return target
