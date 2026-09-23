from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from sro.application.induction.capabilities import ReadCapability, reads_about, wrote_to
from sro.application.induction.headers import build_header_plans
from sro.application.induction.sites import url_path_segments
from sro.application.knowledge.open_questions import Ambiguity
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import Verdict


def ambiguity_in(frames: tuple[ActionFrame, ...], taught: ObjectiveKey) -> Ambiguity | None:
    reads = reads_about(frames, taught.entity_type)
    written = wrote_to(frames)
    if not reads or not written:
        return None
    if reads[0].entity.lower() == written.lower():
        return None

    entity = taught.entity_type.replace("_", " ")
    return Ambiguity(
        system=taught.target_system,
        key=f"{taught.target_system}/{taught.entity_type}/collection",
        question=(
            f'When somebody says "{entity}", do they mean the ones at '
            f"{taught.facility}, or all of them?"
        ),
        options=(reads[0].entity, written),
        because=(
            f"{reads[0].entity} returned {reads[0].rows} when this was demonstrated",
            f"{written} is what the task writes to, and is wider",
        ),
    )


def read_skills(
    frames: tuple[ActionFrame, ...],
    *,
    prefer: str | None = None,
    taught: ObjectiveKey,
    recording_id: RecordingId,
    tenant_id: object,
    by: PrincipalId,
    at: datetime,
    new_id: object,
) -> tuple[Skill, ...]:
    return tuple(
        _skill(
            capability,
            taught=taught,
            recording_id=recording_id,
            tenant_id=tenant_id,
            by=by,
            at=at,
            written=wrote_to(frames),
            skill_id=new_id(),  # type: ignore[operator]
        )
        for capability in _chosen(frames, taught, prefer)[:1]
    )


def _chosen(
    frames: tuple[ActionFrame, ...], taught: ObjectiveKey, prefer: str | None
) -> tuple[ReadCapability, ...]:
    captured = reads_about(frames, taught.entity_type)
    if not prefer or (captured and captured[0].entity.lower() == prefer.lower()):
        return captured

    write = _write_request(frames)
    if write is None or _resource(write.url).lower() != prefer.lower():
        return captured
    return (ReadCapability(replace(write, method="GET", url=write.url.split("?")[0]), prefer, -1),)


def _write_request(frames: tuple[ActionFrame, ...]) -> CapturedRequest | None:
    for frame in reversed(frames):
        for request in frame.requests:
            if request.is_mutation and request.status and 200 <= request.status < 300:
                return request
    return None


def _resource(url: str) -> str:
    return url_path_segments(url)[-1]


def objective_for(capability: ReadCapability, taught: ObjectiveKey) -> ObjectiveKey:
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
    written: str | None,
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

    narrower = bool(written) and capability.entity.lower() != (written or "").lower()
    where = f" at {taught.facility}" if narrower else ""

    skill = Skill(
        id=SkillId(str(skill_id)),
        tenant_id=tenant_id,  # type: ignore[arg-type]
        objective_key=objective,
        name=(f"List {entity}s{where}" if listing else f"View {entity}{where}"),
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
                    expected_status=200
                    if capability.rows < 0
                    else (capability.request.status or 200),
                ),
                assertions=(
                    Assertion(
                        kind=AssertionKind.HTTP_STATUS,
                        expected=Template(
                            "200" if capability.rows < 0 else str(capability.request.status or 200)
                        ),
                    ),
                ),
            ),
        ),
        parameters=(),
        provenance=Provenance(
            recording_ids=(recording_id,),
            aligned_recording_ids=(recording_id,),
            induced_at=at,
            induced_by=by,
            note=(
                f"observed while {taught.objective_type} was demonstrated: the screen read "
                f"{capability.entity} before anybody touched it"
            ),
        ),
        summary=(
            f"{'List every' if listing else 'View a'} {entity} "
            f"at {taught.facility} on {taught.target_system}, as {capability.entity}."
            + (
                f" The task itself writes to {written}, which is a wider collection."
                if narrower
                else ""
            )
            + (
                f" There were {capability.counted} when this was observed."
                if listing and capability.counted
                else ""
            )
        ),
        when_to_use=(
            f"Use to answer questions about {entity} — how many there are, "
            f"which exist, what one of them says."
        ),
    )
    skill.add_version(version)
    version.earn(Verdict.WITHHELD, at)
    return skill
