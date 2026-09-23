from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.errors import InvariantViolation, NotFound
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import TrackRecord


@dataclass(frozen=True, slots=True)
class Asserted:
    skill_id: SkillId
    version: int
    step_index: int


class AddAssertion:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        version: int,
        step_index: int,
        kind: AssertionKind,
        expected: str,
        pointer: str | None = None,
    ) -> Asserted:
        now = self._clock.now()

        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            source = skill.version(version)
            step = _step_at(source, step_index)

            written = Assertion(
                kind=kind,
                expected=Template(expected),
                pointer=pointer or None,
                written_by=ctx.principal_id,
            )
            _refuse_unless_declared(source, written)
            _refuse_unless_checkable(step, written)
            _refuse_if_already_there(step, written)

            fresh = replace(
                source,
                version=skill.next_version_number(),
                steps=tuple(
                    replace(each, assertions=(*each.assertions, written))
                    if each.index == step_index
                    else each
                    for each in source.steps
                ),
                stage=PromotionStage.RECORDED,
                track_record=TrackRecord(),
                promoted_at=None,
                promoted_by=None,
                promoted_from="",
                demotion_reason=None,
                provenance=replace(
                    source.provenance,
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=_note(step_index, written, at=now),
                ),
            )
            skill.add_version(fresh)
            await uow.skills.save(skill)
            await uow.commit()

        return Asserted(skill_id=skill_id, version=fresh.version, step_index=step_index)


def _step_at(version: SkillVersion, index: int) -> SkillStep:
    for step in version.steps:
        if step.index == index:
            return step
    raise NotFound(f"version {version.version} has no step {index}")


def _refuse_unless_declared(version: SkillVersion, written: Assertion) -> None:
    declared = {parameter.name for parameter in version.parameters}
    missing = sorted(written.expected.placeholders - declared)
    if missing:
        raise InvariantViolation("this skill has no parameter called " + ", ".join(missing))


def _refuse_unless_checkable(step: SkillStep, written: Assertion) -> None:
    if step.tool_plan is None or step.network_plan is not None:
        return
    if written.kind in (AssertionKind.HTTP_STATUS, AssertionKind.UI_TEXT_VISIBLE):
        raise InvariantViolation(
            f"a {written.kind.value} assertion cannot be checked against what a tool "
            "answers, which is a document with no status code and no screen. Assert on "
            "a field of the answer instead"
        )


def _refuse_if_already_there(step: SkillStep, written: Assertion) -> None:
    for existing in step.assertions:
        if (existing.kind, str(existing.expected), existing.pointer) == (
            written.kind,
            str(written.expected),
            written.pointer,
        ):
            raise InvariantViolation("this step already checks that")


def _note(index: int, written: Assertion, *, at: datetime) -> str:
    where = f" at {written.pointer}" if written.pointer else ""
    return (
        f"step {index} now checks {written.kind.value}{where} is {written.expected}, "
        f"written on {at.date().isoformat()}"
    )
