"""Turn two sealed recordings into a skill version."""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.induction import assertions as assertion_extraction
from sro.application.induction.diff import Parameterisation, parameterise
from sro.application.induction.emit import emit_step
from sro.application.induction.errors import InductionFailed
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion


@dataclass(frozen=True, slots=True)
class InducedSkill:
    skill_id: SkillId
    version: int
    step_count: int
    input_parameter_count: int
    derived_parameter_count: int


class InduceSkill:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId,
        name: str | None = None,
    ) -> InducedSkill:
        now = self._clock.now()

        async with self._uow as uow:
            run_a = await uow.recordings.get(ctx.tenant_id, first)
            run_b = await uow.recordings.get(ctx.tenant_id, second)
            _check_pairable(run_a, run_b)

            parameterisation = parameterise(run_a.frames, run_b.frames)
            steps = _build_steps(run_a, run_b, parameterisation)

            skill = await uow.skills.find_by_objective(ctx.tenant_id, run_a.objective_key)
            if skill is None:
                skill = Skill(
                    id=self._ids.new_skill_id(),
                    tenant_id=ctx.tenant_id,
                    objective_key=run_a.objective_key,
                    name=name or run_a.objective_key.objective_type.replace("_", " ").title(),
                    created_at=now,
                )
                await uow.skills.add(skill)

            version = SkillVersion(
                version=skill.next_version_number(),
                steps=steps,
                parameters=parameterisation.parameters,
                provenance=Provenance(
                    recording_ids=(run_a.id, run_b.id),
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=_provenance_note(run_a, run_b),
                ),
            )
            skill.add_version(version)
            await uow.skills.save(skill)
            await uow.commit()

        return InducedSkill(
            skill_id=skill.id,
            version=version.version,
            step_count=len(version.steps),
            input_parameter_count=len(version.inputs),
            derived_parameter_count=len(version.parameters) - len(version.inputs),
        )


def _check_pairable(run_a: Recording, run_b: Recording) -> None:
    if run_a.id == run_b.id:
        raise InductionFailed(
            "a skill needs two different recordings; diffing one against itself would "
            "hardcode every value in it"
        )
    for recording in (run_a, run_b):
        if recording.status is not RecordingStatus.SEALED:
            raise InductionFailed(
                f"recording {recording.id} is {recording.status}; only sealed recordings "
                "can be induced"
            )
    if run_a.objective_key != run_b.objective_key:
        raise InductionFailed(
            f"the recordings describe different objectives "
            f"({run_a.objective_key.slug()} and {run_b.objective_key.slug()})"
        )


def _build_steps(
    run_a: Recording, run_b: Recording, parameterisation: Parameterisation
) -> tuple[SkillStep, ...]:
    frames_a, frames_b = run_a.frames, run_b.frames
    return tuple(
        emit_step(
            index,
            frames_a[index],
            parameterisation,
            assertion_extraction.extract(
                frames_a[index],
                frames_b[index],
                next_a=frames_a[index + 1] if index + 1 < len(frames_a) else None,
                next_b=frames_b[index + 1] if index + 1 < len(frames_b) else None,
            ),
            run_a.objective_key,
            frames_b[index],
        )
        for index in range(len(frames_a))
    )


def _provenance_note(run_a: Recording, run_b: Recording) -> str:
    narrated = [r.id for r in (run_a, run_b) if r.has_narration]
    if not narrated:
        return "induced from two silent demonstrations"
    return f"narration available on {', '.join(str(rid) for rid in narrated)}"
