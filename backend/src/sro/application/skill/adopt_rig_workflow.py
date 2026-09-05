"""A workflow the rig mined, adopted into the skill library.

`version_from_rig` builds a `SkillVersion` and stops, because a `Skill` needs
an `ObjectiveKey` -- objective type, target system, entity type, facility,
direction -- and the rig produces none of those. It knows a title, the systems
a job touched and a shape key. Deriving "an inbound receipt against BLR1" from
`Create Work Area NEWTESTS` would be a guess wearing the clothes of a finding.

So this is the seam where a person joins in, and the whole design of the module
is about keeping the two contributions distinguishable afterwards:

- **The rig produced the version.** `induced_by` is the rig, not the person who
  adopted it. `Provenance.induced_by` says "who produced this version", and its
  own docstring makes the point that `drift-repair` goes there where the system
  did the work and "does not pretend to be" a person. A model reading 170 hours
  of capture is the same kind of author.
- **A person chose to adopt it, and named what it is for.** That is a decision
  with somebody's name on it, so it goes in the note where a reviewer reads it.

Nothing arrives promoted. `add_version` refuses anything but RECORDED, and that
is the right refusal: the objective is a person's reading of a title, and the
steps are a model's reading of a day. Neither has been checked against the
other by anybody.

Nothing here reaches for the rig either. The evidence arrives as the shape
`GET /v1/workflows/{id}/evidence` serves, from whatever fetched it -- so the
two systems share a shape rather than a dependency, and a caller can adopt a
workflow out of a file as easily as out of a running rig.
"""

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
"""The author of these steps. A model reading a day of capture is not a person
and does not pretend to be one -- the same reasoning `drift-repair` carries."""


@dataclass(frozen=True, slots=True)
class Adopted:
    skill_id: SkillId
    version: SkillVersion
    created_the_skill: bool
    """False where this is a second reading of a job the library already knew.
    A reviewer comparing two versions of one objective is the point of saying
    so: the rig watching the same job twice is evidence, not a duplicate."""


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
        """Adopt one mined workflow under an objective a person has named.

        The facility comes from the objective rather than from a second
        argument. A credential reference is a vault key scoped per system and
        facility, and the objective is the only place this system records which
        facility a job belongs to -- taking it separately would let a caller
        file a Bengaluru job's credentials under Singapore by passing two
        arguments that disagree.
        """
        now = self._clock.now()
        async with self._uow as uow:
            skill = await uow.skills.find_by_objective(ctx.tenant_id, objective)
            version = version_from_rig(
                workflow,
                gestures,
                recordings=recordings,
                induced_by=str(RIG),
                induced_at=now,
                # Sequential and append-only. A second reading of a job the
                # library already knows is v2, never a replacement: existing
                # versions are what runs are judged against.
                version=skill.next_version_number() if skill else 1,
                requests=requests,
                facility=objective.facility,
            )
            if version is None:
                raise DomainError(
                    "this workflow has no runnable step, or no recording it came "
                    "from -- there is nothing to adopt"
                )
            # Everything the person contributed, where a reviewer looking at the
            # version reads it. `induced_by` is the rig because the rig wrote
            # the steps; this is the other half.
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
    """The workflow's own title, where it has a usable one.

    `str()` of whatever was there put `{'a': 1}` in a library as a skill name.
    A title is a string or it is nothing, and the objective's slug is a better
    fallback than a rendered dict.
    """
    title = workflow.get("title")
    return title.strip() if isinstance(title, str) else ""


def _adopted_by(
    version: SkillVersion, principal: PrincipalId, objective: ObjectiveKey
) -> Provenance:
    """The provenance, with who adopted it and under what name appended.

    A sentence rather than a field, because "who pressed adopt" is not a
    question any screen filters a library by -- unlike "was this written by a
    person or by the system", which has `induced_by` and `repaired_from`
    already. What it must not do is go unrecorded: the objective is the one
    part of this version nobody derived from evidence.
    """
    said = version.provenance.note
    mine = f"adopted from the rig by {principal} as {objective.slug()}"
    return replace(version.provenance, note=f"{said}\n\n{mine}" if said else mine)
