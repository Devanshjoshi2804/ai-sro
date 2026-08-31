"""Mapping a step onto a connector's tool, which is the one part of a skill
nobody demonstrates.

Induction reads recordings, and a recording holds gestures and the calls they
made. So this is always somebody's decision, and what these tests hold is that
it is recorded as one -- and that a version which has been mapped starts at the
bottom of the ladder rather than inheriting a streak earned by the clicks it
replaced.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.ports.tools import ToolOffered
from sro.application.skill.map_step_to_tool import MapStepToTool
from sro.domain.recording.events import ActionKind
from sro.domain.shared.errors import InvariantViolation, NotFound
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeToolCaller, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SUPPLIER = f.parameter(name="supplier", observed_values=("a@b.test", "c@d.test"))
OFFERS = {
    "mail": (ToolOffered(name="send_message", description="Send a mail", arguments=("to", "body")),)
}


def _clicked() -> SkillStep:
    """The step somebody taught by pressing Send."""
    return SkillStep(
        index=1,
        intent="send the reply",
        ui_plan=UiPlan(action=ActionKind.CLICK, target=f.fingerprint(accessible_name="Send")),
    )


async def _mapped(
    uow: FakeUnitOfWork,
    *,
    arguments: dict[str, str] | None = None,
    server: str = "mail",
    tool: str = "send_message",
    writes: bool = True,
    step_index: int = 1,
    tools: FakeToolCaller | None = None,
) -> object:
    return await MapStepToTool(uow, FakeClock(), tools or FakeToolCaller(offers=OFFERS)).execute(
        CTX,
        skill_id=f.SkillId("skill-1"),
        version=1,
        step_index=step_index,
        server=server,
        tool=tool,
        arguments=arguments if arguments is not None else {"to": "${supplier}"},
        writes=writes,
    )


async def _stored(uow: FakeUnitOfWork) -> None:
    # The factory's own step, whose parameter is declared beside the one the
    # mapping will use.
    version = f.skill_version(
        steps=(f.step(index=0), _clicked()), parameters=(f.parameter(), SUPPLIER)
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    # Promoted after it is on the skill, the way a reviewer does it: a version
    # is added at RECORDED and walks up from there.
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


async def test_the_step_becomes_a_call_and_the_rest_is_left_alone() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _mapped(uow)

    fresh = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[-1]
    assert fresh.steps[1].tool_plan is not None
    assert fresh.steps[1].tool_plan.tool == "send_message"
    # The gesture is kept beside it rather than replaced: which way a step was
    # performed is what the medium on the outcome says, and a version that
    # threw the click away could never be run in the interface again.
    assert fresh.steps[1].ui_plan is not None
    assert fresh.steps[0].tool_plan is None


async def test_a_mapping_is_a_new_version_and_not_an_edit() -> None:
    """A version that changed under a reviewer who had already read it is a
    review of something else."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _mapped(uow)

    skill = await uow.skills.get(f.TENANT, f.SkillId("skill-1"))
    assert len(skill.versions) == 2
    assert skill.versions[0].steps[1].tool_plan is None


async def test_the_mapped_version_starts_at_the_bottom_of_the_ladder() -> None:
    """A repair inherits its rung, because one locator changed and every value
    is still the one the demonstrations carried. This is a step going through a
    door nobody has watched it go through: the streak that would let it run
    unattended has to be earned against the connector."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _mapped(uow)

    fresh = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[-1]
    assert fresh.stage is PromotionStage.RECORDED
    assert fresh.track_record.clean_streak == 0


async def test_it_says_who_decided_and_what_they_decided() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _mapped(uow)

    fresh = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[-1]
    assert fresh.provenance.induced_by == f.OPERATOR
    assert "was a gesture and is now send_message on mail" in fresh.provenance.note
    # The recordings stay: every other step, and every value this one sends,
    # still came from them.
    assert fresh.provenance.recording_ids


async def test_a_tool_the_connector_does_not_offer_is_refused_before_the_version_exists() -> None:
    """A skill carrying a mapping onto a tool that does not exist looks exactly
    like a working one until somebody fires it -- and by then the click it
    replaced has been mapped away."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(InvariantViolation, match="offers no tool called"):
        await _mapped(uow, tool="delete_everything")

    assert len((await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions) == 1


async def test_a_deployment_with_no_connector_is_told_so() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(InvariantViolation, match="no connector is configured"):
        await _mapped(uow, tools=FakeToolCaller(available=False))


async def test_an_argument_naming_a_parameter_that_does_not_exist_is_refused() -> None:
    """`SkillVersion` would refuse this too, as an invariant violation -- which
    reads as a bug in this system rather than as a typo in the form somebody
    just filled in."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(InvariantViolation, match="no parameter called recipient"):
        await _mapped(uow, arguments={"to": "${recipient}"})

    assert len((await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions) == 1


async def test_a_step_that_is_not_there_is_refused_rather_than_quietly_doing_nothing() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow)

    with pytest.raises(NotFound, match="no step 7"):
        await _mapped(uow, step_index=7)


async def test_a_mapped_write_that_checks_nothing_still_cannot_reach_autonomy() -> None:
    """No special case for a mapped step. Nobody demonstrated this call, so its
    post-conditions are somebody's writing -- and a write with no assertion has
    always made a version unverifiable."""
    uow = FakeUnitOfWork()
    await _stored(uow)

    await _mapped(uow, writes=True)

    fresh = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[-1]
    assert fresh.changes_the_system is True
    assert 1 in fresh.unchecked_writes
    assert fresh.verifiable is False


async def test_the_gesture_ceiling_lifts_once_every_step_is_a_call() -> None:
    """The whole point. `needs_a_person` is what says a version can never hold
    a clean streak, and it reads "no network plan and no tool plan"."""
    uow = FakeUnitOfWork()
    await _stored(uow)
    before = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[0]
    assert before.needs_a_person is True

    await _mapped(uow)

    fresh = (await uow.skills.get(f.TENANT, f.SkillId("skill-1"))).versions[-1]
    assert fresh.needs_a_person is False
