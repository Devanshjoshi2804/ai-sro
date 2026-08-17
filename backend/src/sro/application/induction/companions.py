"""Skills a demonstration proved without being about them.

Teaching "create a transport mode" opens the screen, and opening the screen
lists the ones that already exist. That list is a real GET with a real 200 and a
real body -- so "how many transport modes are there" is answerable from evidence
already in hand, and asking the operator to demonstrate it separately is asking
them for something we have.

These are built beside the taught skill, never instead of it, and only ever
from reads. They start where any read starts and climb on their own record like
everything else.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.induction.capabilities import ReadCapability, reads_about
from sro.application.induction.headers import build_header_plans
from sro.domain.recording.events import ActionFrame
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import Verdict


def read_skills(
    frames: tuple[ActionFrame, ...],
    *,
    taught: ObjectiveKey,
    recording_id: RecordingId,
    tenant_id: object,
    by: PrincipalId,
    at: datetime,
    new_id: object,
) -> tuple[Skill, ...]:
    """One skill per read the demonstration made about its own entity."""
    return tuple(
        _skill(
            capability,
            taught=taught,
            recording_id=recording_id,
            tenant_id=tenant_id,
            by=by,
            at=at,
            skill_id=new_id(),  # type: ignore[operator]
        )
        for capability in reads_about(frames, taught.entity_type)
    )


def objective_for(capability: ReadCapability, taught: ObjectiveKey) -> ObjectiveKey:
    """A read of the same entity, at the same site, named for what it does."""
    return ObjectiveKey(
        objective_type="list" if capability.rows != 1 else "view",
        target_system=taught.target_system,
        entity_type=taught.entity_type,
        facility=taught.facility,
        direction=Direction.INTERNAL,
    )


def _skill(
    capability: ReadCapability,
    *,
    taught: ObjectiveKey,
    recording_id: RecordingId,
    tenant_id: object,
    by: PrincipalId,
    at: datetime,
    skill_id: object,
) -> Skill:
    entity = taught.entity_type.replace("_", " ")
    listing = capability.rows != 1
    objective = objective_for(capability, taught)

    skill = Skill(
        id=SkillId(str(skill_id)),
        tenant_id=tenant_id,  # type: ignore[arg-type]
        objective_key=objective,
        name=f"{'List' if listing else 'View'} {entity}",
        created_at=at,
    )
    version = SkillVersion(
        version=1,
        steps=(
            SkillStep(
                index=0,
                intent=f"read the {entity} the system holds",
                network_plan=NetworkPlan(
                    method="GET",
                    url=Template(capability.request.url),
                    headers=build_header_plans(
                        capability.request,
                        target_system=taught.target_system,
                        facility=taught.facility,
                    ),
                    expected_status=capability.request.status or 200,
                ),
                # The only assertion a read needs, and the one that makes it
                # verifiable: it answered the way it answered for the human.
                assertions=(
                    Assertion(
                        kind=AssertionKind.HTTP_STATUS,
                        expected=Template(str(capability.request.status or 200)),
                    ),
                ),
            ),
        ),
        parameters=(),
        provenance=Provenance(
            recording_ids=(recording_id,),
            induced_at=at,
            induced_by=by,
            note=(
                f"observed while {taught.objective_type} was demonstrated: the screen read "
                f"{capability.entity} before anybody touched it"
            ),
        ),
        summary=(
            f"{'List the' if listing else 'View a'} {entity} "
            f"at {taught.facility} on {taught.target_system}."
            + (f" {capability.rows} were there when this was observed." if listing else "")
        ),
        when_to_use=(
            f"Use to answer questions about {entity} — how many there are, "
            f"which exist, what one of them says."
        ),
    )
    skill.add_version(version)
    # A read is the safest thing in the system and nothing about it is withheld
    # at the next rung, so it starts where every other version starts and takes
    # the same first step immediately.
    version.earn(Verdict.WITHHELD, at)
    return skill
