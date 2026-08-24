"""A recorded Blue Yonder flow, taught without anyone demonstrating it again.

Blue Yonder gives this system no tools or docs of its own -- what stands in for
them is a corpus of recorded call cascades. This is the seam that turns one of
those into a reviewable skill, at the same trust level a single live
demonstration always earns: RECORDED, proposed parameters, never promoted just
for having come from a file instead of a click.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.induction.seed_from_flow import SeedSkillFromFlow
from sro.application.induction.understand import UnderstandRecording
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
CODE = "ACME-2"

FLOW = {
    "spec": "suppliers",
    "resource": "suppliers",
    "applied": {"code": CODE},
    "invalid": [],
    "calls": [
        {
            "endpoint": "wm/suppliers",
            "request": {
                "method": "POST",
                "url": "https://wms.test/api/suppliers",
                "headers": {"content-type": "application/json"},
                "body": f'{{"code": "{CODE}", "status": "active"}}',
            },
            "startedAt": 0,
            "response": {
                "status": 201,
                "headers": {},
                "body": f'{{"code": "{CODE}", "status": "active"}}',
            },
        }
    ],
}


def _seeder(uow: FakeUnitOfWork) -> SeedSkillFromFlow:
    return SeedSkillFromFlow(
        uow,
        FakeClock(),
        FakeIdFactory(),
        UnderstandRecording(uow, NoInterpreter(), FakeClock(), FakeIdFactory()),
    )


async def test_a_flow_becomes_a_recorded_skill_with_a_real_parameter() -> None:
    uow = FakeUnitOfWork()

    seeded = await _seeder(uow).execute(CTX, flow=FLOW, system="blue_yonder")

    assert seeded.skill_id is not None
    skill = next(iter(uow.skills.rows.values()))
    version = skill.versions[-1]
    # Straight to shadow, the same as any single-demonstration teach: reads go
    # out for real, writes are withheld, nothing runs unattended yet.
    assert version.stage is PromotionStage.SHADOW

    typed = [p for p in version.parameters if p.kind is ParameterKind.INPUT]
    assert [p.observed_values for p in typed] == [(CODE,)]

    plan = version.steps[0].network_plan
    assert plan is not None
    assert plan.body is not None
    assert CODE not in plan.body.raw


async def test_seeding_the_same_flow_twice_seeds_once() -> None:
    uow = FakeUnitOfWork()
    seeder = _seeder(uow)

    first = await seeder.execute(CTX, flow=FLOW, system="blue_yonder")
    second = await seeder.execute(CTX, flow=FLOW, system="blue_yonder")

    assert first.skill_id is not None
    assert second.skill_id == first.skill_id
    assert second.skipped == "already seeded"
    assert len(uow.skills.rows) == 1


async def test_a_flow_with_no_calls_is_skipped_not_failed() -> None:
    uow = FakeUnitOfWork()
    empty = {"spec": "empty", "resource": "empty", "applied": {}, "calls": []}

    seeded = await _seeder(uow).execute(CTX, flow=empty, system="blue_yonder")

    assert seeded.skill_id is None
    assert seeded.skipped == "this flow has no calls"
    assert uow.skills.rows == {}
