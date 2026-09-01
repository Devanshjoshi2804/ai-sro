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
    """Two readings of one entity, where picking either would be a guess.

    Blue Yonder creates in `transportModes` and refreshes `warehouseTransportModes`:
    sixteen rows at this site, twenty-three across all of them. Both answer "how
    many transport modes are there", and which one somebody means is a fact
    about how they talk, not about the system -- so it is asked, once, rather
    than decided by whichever the screen happened to fetch first.
    """
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
    """The read that answers questions about this entity, if the demonstration
    made one.

    One, not several. A screen reads its subject, and then reads three things
    named after its subject -- unit conversions, defaults, permissions -- and a
    library with four "List transport mode" skills in it is worse than one with
    none, because now somebody has to pick.
    """
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
    """The read to build from, once somebody has said which collection they mean.

    The screen creates in one collection and refreshes another, and only a
    person can say which one their words are about. When they have said, and it
    is not the one the demonstration happened to fetch, the read is built from
    the collection they named -- addressed by the URL the task already writes
    to, which is proven to exist because a 201 came back from it.

    That is the operator's instruction, not an inference: the address is
    evidence, and which collection they mean is theirs to declare.
    """
    captured = reads_about(frames, taught.entity_type)
    if not prefer or (captured and captured[0].entity.lower() == prefer.lower()):
        return captured

    write = _write_request(frames)
    if write is None or _resource(write.url).lower() != prefer.lower():
        return captured
    # No query at all: the site parameters belong to the site's own view, and
    # this collection answers 500 when given them.
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
    written: str | None,
    taught: ObjectiveKey,
    recording_id: RecordingId,
    tenant_id: object,
    by: PrincipalId,
    at: datetime,
    skill_id: object,
) -> Skill:
    entity = taught.entity_type.replace("_", " ")
    # -1 means the collection was named rather than observed: nobody fetched it
    # during the demonstration, so how many it holds is not something to claim.
    listing = capability.rows != 1
    objective = objective_for(capability, taught)

    # The screen creates in one collection and refreshes another: the site's own
    # view of it. Both are real and they answer different questions, so a skill
    # reading the narrower one says which, rather than calling itself the list.
    # Compared raw, not normalised: normalising exists to see through the
    # `warehouse` prefix, and the prefix is exactly the difference here.
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
                    # 200 when the collection was named rather than observed:
                    # the request it was synthesised from was a create, and a
                    # read that expects 201 fails on every success.
                    expected_status=200
                    if capability.rows < 0
                    else (capability.request.status or 200),
                ),
                # The only assertion a read needs, and the one that makes it
                # verifiable: it answered the way it answered for the human.
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
            # The one step this version has -- a read -- is built from what
            # this exact recording observed, not left to the default that
            # means "nobody said". One recording, and it plainly shaped it.
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
    # A read is the safest thing in the system and nothing about it is withheld
    # at the next rung, so it starts where every other version starts and takes
    # the same first step immediately.
    version.earn(Verdict.WITHHELD, at)
    return skill
