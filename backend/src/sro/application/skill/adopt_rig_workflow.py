from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.skill.version_from_rig import version_from_rig
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId, SkillId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Provenance, Skill, SkillVersion

RIG = PrincipalId("rig")


@dataclass(frozen=True, slots=True)
class Adopted:
    skill_id: SkillId
    version: SkillVersion
    created_the_skill: bool


class AdoptRigWorkflow:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow: Mapping[str, object],
        gestures: Mapping[str, Mapping[str, object]],
        recordings: Sequence[str],
        objective: ObjectiveKey,
        requests: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
        name: str = "",
    ) -> Adopted:
        now = self._clock.now()
        async with self._uow as uow:
            skill = await uow.skills.find_by_objective(ctx.tenant_id, objective)
            version = version_from_rig(
                workflow,
                gestures,
                recordings=recordings,
                induced_by=str(RIG),
                induced_at=now,
                version=skill.next_version_number() if skill else 1,
                requests=requests,
                facility=objective.facility,
            )
            if version is None:
                raise DomainError(
                    "this workflow has no runnable step, or no recording it came "
                    "from -- there is nothing to adopt"
                )
            version.provenance = _adopted_by(version, ctx.principal_id, objective)

            created = skill is None
            if skill is None:
                skill = Skill(
                    id=self._ids.new_skill_id(),
                    tenant_id=ctx.tenant_id,
                    objective_key=objective,
                    name=name or _title(workflow) or objective.slug(),
                    created_at=now,
                )
                await uow.skills.add(skill)
            skill.add_version(version)
            await uow.skills.save(skill)
            await uow.commit()
        return Adopted(skill_id=skill.id, version=version, created_the_skill=created)


def _title(workflow: Mapping[str, object]) -> str:
    title = workflow.get("title")
    return title.strip() if isinstance(title, str) else ""


def _adopted_by(
    version: SkillVersion, principal: PrincipalId, objective: ObjectiveKey
) -> Provenance:
    said = version.provenance.note
    mine = f"adopted from the rig by {principal} as {objective.slug()}"
    return replace(version.provenance, note=f"{said}\n\n{mine}" if said else mine)
