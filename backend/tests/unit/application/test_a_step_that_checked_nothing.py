"""A step that checked nothing must not read as a step that passed.

An empty failure list is what a fully verified step returns. It is also what a
step with no post-condition at all returns, and every rule downstream read the
two the same way -- `LearnFromRun` took a claim from an unverified write, and a
reviewer reading the run saw a step that had been tested.

The interface rung already said so, in as many words: silence reads as a passing
check to everything downstream. The rung that runs far more often did not.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    NOTHING_ASSERTED,
    ExecuteSkill,
    ExecutionRequest,
)
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import why_not_autonomous
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

CHECKED = (Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),)


def _write(index: int, *, asserts: bool) -> SkillStep:
    return SkillStep(
        index=index,
        intent="create the work area",
        network_plan=NetworkPlan(
            method="POST",
            url=Template("https://wms.test/api/work-areas"),
            body=Template('{"name":"X"}'),
            expected_status=200,
        ),
        assertions=CHECKED if asserts else (),
    )


def _read(index: int, *, asserts: bool) -> SkillStep:
    return SkillStep(
        index=index,
        intent="find the order",
        network_plan=NetworkPlan(
            method="GET", url=Template("https://wms.test/api/orders"), expected_status=200
        ),
        assertions=CHECKED if asserts else (),
    )


def _why(version: object) -> str | None:
    return why_not_autonomous(
        version.track_record,  # type: ignore[attr-defined]
        verifiable=version.verifiable,  # type: ignore[attr-defined]
        needs_a_person=version.needs_a_person,  # type: ignore[attr-defined]
        unchecked_writes=(
            "step " + ", ".join(str(i) for i in version.unchecked_writes)  # type: ignore[attr-defined]
            if version.unchecked_writes  # type: ignore[attr-defined]
            else "no step"
        ),
    )


def test_a_write_nobody_checks_is_named() -> None:
    version = f.skill_version(steps=(_read(0, asserts=True), _write(1, asserts=False)))

    assert version.unchecked_writes == (1,)


def test_a_read_that_asserts_does_not_cover_for_a_write_that_does_not() -> None:
    """The hole `any` left. One asserting step anywhere made the whole version
    verified, and the step it was standing in for was the one changing the
    warehouse."""
    version = f.skill_version(steps=(_read(0, asserts=True), _write(1, asserts=False)))

    assert version.verifiable is False
    reason = _why(version)
    assert reason is not None
    # Named, not counted: "no step has an assertion" was false here and told
    # whoever read it to go looking in the wrong place.
    assert "step 1" in reason
    assert "never unattended" in reason


def test_a_version_whose_writes_are_all_checked_is_verifiable() -> None:
    version = f.skill_version(steps=(_read(0, asserts=False), _write(1, asserts=True)))

    assert version.verifiable is True
    assert version.unchecked_writes == ()


def test_a_read_only_skill_that_asserts_nothing_is_still_refused() -> None:
    """`all` over no writes is vacuously true, so tightening the rule to writes
    alone would have quietly passed the skill that checks nothing at all."""
    version = f.skill_version(steps=(_read(0, asserts=False), _read(1, asserts=False)))

    assert version.unchecked_writes == ()
    assert version.verifiable is False


@pytest.mark.parametrize(("asserts", "expected"), [(True, ()), (False, (NOTHING_ASSERTED,))])
async def test_a_network_step_says_whether_it_verified_anything(
    asserts: bool, expected: tuple[str, ...]
) -> None:
    """What the outcome carries, run for real.

    `LearnFromRun` reads this before it believes anything a run says, and a
    reviewer reads it to know whether the step was tested. Both were told the
    same thing by a checked step and by one with no post-condition at all.
    """
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    version = f.skill_version(steps=(_write(0, asserts=asserts),), parameters=())
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(skill_id=skill.id, parameters={}, authorized_by="supervisor"),
    )

    run = next(iter(uow.runs.rows.values()))
    assert run.steps[0].assertion_failures == ()
    assert run.steps[0].unchecked == expected
