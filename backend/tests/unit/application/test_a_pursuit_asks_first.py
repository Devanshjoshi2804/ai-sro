"""What a pursuit is refused for, before a browser opens.

The rung with no demonstration behind it was the one with no gate. ``execute``
checked that a vision driver existed and that the system was connected, then
drove a signed-in WMS for twelve gestures. Its own module docstring said the
operator's confirmation was carried and everything that makes the other rungs
safe applied here "and matters more"; neither the confirmation nor the breaker
was in the code.
"""

from __future__ import annotations

import pytest

from sro.application.connection.browsers import Browsers
from sro.application.context import RequestContext
from sro.application.execution.execute_skill import Refused
from sro.application.execution.pursue_goal import PursueGoal, Unauthorised
from sro.application.intent.pursue import compose
from sro.application.ports.vision import VisionUnavailable
from sro.domain.execution.run import Run, RunId
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SYSTEM = "blue_yonder"
A_WRITE = "create a transport mode called SROTEST9"
A_READ = "how many transport modes are there"


def _pursuit(uow: FakeUnitOfWork, *, sees: object = None) -> PursueGoal:
    """``sees`` stands in for the vision and UI rungs. The tests below all stop
    before either is used -- the point is which refusal comes first."""
    provider, clock = FakeBrowserProvider(), FakeClock()
    return PursueGoal(
        uow,
        FakeCredentialVault(),
        provider,
        sees,  # type: ignore[arg-type]
        sees,  # type: ignore[arg-type]
        clock,
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        Browsers(provider, uow, clock, FakeIdFactory()),
        egress_enabled=True,
    )


async def _failed_runs(uow: FakeUnitOfWork, how_many: int) -> None:
    for index in range(how_many):
        run = Run(
            id=RunId(f"old-{index}"),
            tenant_id=f.TENANT,
            skill_id=SkillId("skill-1"),
            skill_version=1,
            stage=PromotionStage.ASSISTED,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=f.at(800),
            authorized_by=f.OPERATOR,
            target_system=SYSTEM,
        )
        run.fail(f.at(900), "the system answered 500")
        await uow.runs.add(run)


async def test_a_goal_that_would_write_is_refused_with_nobody_on_the_record() -> None:
    with pytest.raises(Unauthorised, match="nobody confirmed"):
        await _pursuit(FakeUnitOfWork()).execute(
            CTX, goal=compose(A_WRITE, None), target_system=SYSTEM, values={}
        )


async def test_confirming_it_gets_past_that_gate() -> None:
    """As far as the next one, which is about this deployment rather than
    about permission: there is no rung here that can look at a screen."""
    with pytest.raises(VisionUnavailable):
        await _pursuit(FakeUnitOfWork()).execute(
            CTX,
            goal=compose(A_WRITE, None),
            target_system=SYSTEM,
            values={},
            authorized_by="clerk@acme.test",
        )


async def test_a_system_whose_runs_keep_failing_is_not_pursued_either() -> None:
    """A breaker that stops replays while the vision rung keeps driving is not
    a breaker: the same broken screen, with less evidence behind it."""
    uow = FakeUnitOfWork()
    await _failed_runs(uow, 3)

    with pytest.raises(Refused):
        await _pursuit(uow, sees=object()).execute(
            CTX, goal=compose(A_READ, None), target_system=SYSTEM, values={}, authorized_by="clerk"
        )
