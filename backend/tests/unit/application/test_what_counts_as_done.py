"""Somebody writing what counts as a step having worked.

Post-conditions normally come out of the recordings: two demonstrations
answered the same status, or agreed on a field of the response, and that
agreement is evidence. A step performed through a connector has none behind it
-- nobody watched `send_message` work -- so its only possible post-condition is
one a person writes.

Without that, mapping a step reaches exactly one rung short of the thing it
exists for: a write that proves nothing about its result makes the version
unverifiable, and an unverifiable version may run assisted forever and never
unattended.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.skill.add_assertion import AddAssertion
from sro.domain.shared.errors import InvariantViolation, NotFound
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import ToolPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SUPPLIER = f.parameter(name="supplier", observed_values=("a@b.test", "c@d.test"))


def _sends() -> SkillStep:
    """A step mapped onto a connector, with nothing checking the answer."""
    return SkillStep(
        index=1,
        intent="send the reply",
        tool_plan=ToolPlan(
            server="mail",
            tool="send_message",
            arguments=(("to", Template("${supplier}")),),
            writes=True,
        ),
    )


async def _stored(uow: FakeUnitOfWork, *, step: SkillStep | None = None) -> None:
    version = f.skill_version(
        # The first step is checked already, so the only unchecked write in
        # this version is the one under test.
        steps=(
            f.step(
                index=0,
                assertions=(Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),),
            ),
            step or _sends(),
        ),
        parameters=(f.parameter(), SUPPLIER),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


async def _wrote(
    uow: FakeUnitOfWork,
    *,
    kind: AssertionKind = AssertionKind.RESPONSE_FIELD_EQUALS,
    expected: str = "sent",
    pointer: str | None = "/status",
    step_index: int = 1,
) -> object:
    return await AddAssertion(uow, FakeClock()).execute(
        CTX,
        skill_id=SkillId("skill-1"),
        version=1,
        step_index=step_index,
        kind=kind,
        expected=expected,
        pointer=pointer,
    )


async def _latest(uow: FakeUnitOfWork) -> object:
    return (await uow.skills.get(f.TENANT, SkillId("skill-1"))).versions[-1]


async def test_writing_one_is_what_makes_a_mapped_write_verifiable() -> None:
    """The whole reason this exists. Mapping a step onto a tool leaves it
    changing something and proving nothing, and an unverifiable version never
    reaches the top of the ladder however clean its runs are."""
    uow = FakeUnitOfWork()
    await _stored(uow)
    before = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).versions[0]
    assert before.verifiable is False
    assert 1 in before.unchecked_writes

    await _wrote(uow)

    fresh = await _latest(uow)
    assert fresh.verifiable is True  # type: ignore[attr-defined]
    assert fresh.unchecked_writes == ()  # type: ignore[attr-defined]


async def test_it_says_who_decided_that_this_counts_as_success() -> None:
    """A reviewer has to be able to tell a measurement from an opinion. An
    assertion induction derived is what two demonstrations agreed on; this one
    is somebody's decision, and a system that showed them in the same words
    would be presenting a guess as evidence."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _wrote(uow)

    written = (await _latest(uow)).steps[1].assertions[-1]  # type: ignore[attr-defined]
    assert written.written_by == f.OPERATOR


async def test_an_assertion_induction_derived_still_says_nobody_wrote_it() -> None:
    uow = FakeUnitOfWork()
    derived = Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200"))
    await _stored(uow, step=f.step(index=1, assertions=(derived,)))

    await _wrote(uow, kind=AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id", expected="")

    assertions = (await _latest(uow)).steps[1].assertions  # type: ignore[attr-defined]
    assert assertions[0].written_by is None
    assert assertions[1].written_by == f.OPERATOR


async def test_it_only_ever_adds() -> None:
    """A check induction derived is what two demonstrations agreed on, and an
    opinion that could delete a measurement is not a tightening."""
    uow = FakeUnitOfWork()
    derived = Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200"))
    await _stored(uow, step=f.step(index=1, assertions=(derived,)))

    await _wrote(uow, kind=AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id", expected="")

    assert len((await _latest(uow)).steps[1].assertions) == 2  # type: ignore[attr-defined]


async def test_the_version_starts_at_the_bottom_of_the_ladder() -> None:
    """A streak earned before this check existed is not evidence that this
    check passes: every run in it succeeded without ever being asked."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _wrote(uow)

    fresh = await _latest(uow)
    assert fresh.stage is PromotionStage.RECORDED  # type: ignore[attr-defined]
    assert fresh.track_record.clean_streak == 0  # type: ignore[attr-defined]


@pytest.mark.parametrize("kind", [AssertionKind.HTTP_STATUS, AssertionKind.UI_TEXT_VISIBLE])
async def test_a_question_a_tool_can_never_answer_is_refused(kind: AssertionKind) -> None:
    """A tool answers a document: no status code, no screen. An assertion
    nothing can ever check does not make a step safer -- it makes every run of
    it fail, which reads on a screen exactly like a step that is broken."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(InvariantViolation, match="cannot be checked against what a tool"):
        await _wrote(uow, kind=kind, expected="200", pointer=None)

    assert len((await uow.skills.get(f.TENANT, SkillId("skill-1"))).versions) == 1


async def test_the_same_check_twice_is_refused_rather_than_stored_twice() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)
    await _wrote(uow)
    # The second one is written against the version that already has it.
    await AddAssertion(uow, FakeClock()).execute(
        CTX,
        skill_id=SkillId("skill-1"),
        version=1,
        step_index=1,
        kind=AssertionKind.RESPONSE_FIELD_PRESENT,
        expected="",
        pointer="/id",
    )

    with pytest.raises(InvariantViolation, match="already checks that"):
        await AddAssertion(uow, FakeClock()).execute(
            CTX,
            skill_id=SkillId("skill-1"),
            version=2,
            step_index=1,
            kind=AssertionKind.RESPONSE_FIELD_EQUALS,
            expected="sent",
            pointer="/status",
        )


async def test_a_value_naming_a_parameter_that_does_not_exist_is_refused() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(InvariantViolation, match="no parameter called recipient"):
        await _wrote(uow, expected="${recipient}")


async def test_a_step_that_is_not_there_is_refused() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(NotFound, match="no step 9"):
        await _wrote(uow, step_index=9)


async def test_a_network_step_may_be_checked_by_hand_too() -> None:
    """Adding a check to a step that has proven ones is strictly a tightening,
    and the two are told apart by who wrote them rather than by refusing one."""
    uow = FakeUnitOfWork()
    await _stored(uow, step=f.step(index=1))

    await _wrote(uow, kind=AssertionKind.HTTP_STATUS, expected="201", pointer=None)

    written = (await _latest(uow)).steps[1].assertions[-1]  # type: ignore[attr-defined]
    assert written.written_by == f.OPERATOR
