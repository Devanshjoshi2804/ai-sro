"""A task worked out on screen should never have to be worked out twice.

The slow rung exists to make itself unnecessary: a pursuit is captured exactly
as a demonstration is, and what it proves becomes a skill that runs over the API
the next time somebody asks.

The guard is what these are mostly about. A pursuit that ran out of budget half
way through a form recorded a half-filled form, and a skill induced from that
would teach the system to do the wrong thing quickly -- and it would look
exactly as trustworthy as one somebody demonstrated.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.pursue_goal import PursueGoal
from sro.application.intent.pursue import compose
from sro.application.ports.vision import VisionUnavailable
from sro.domain.shared.identifiers import RecordingId
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


class _Capture:
    def __init__(self) -> None:
        self.stopped: list[str] = []

    async def stop(self, ctx: RequestContext, *, recording_id: object) -> None:
        self.stopped.append(str(recording_id))


class _Finish:
    def __init__(self) -> None:
        self.sealed: list[str] = []
        self.abandoned: list[tuple[str, str]] = []

    async def seal(self, ctx: RequestContext, *, recording_id: object, **_: object) -> None:
        self.sealed.append(str(recording_id))

    async def abandon(self, ctx: RequestContext, *, recording_id: object, reason: str) -> None:
        self.abandoned.append((str(recording_id), reason))


class _Understand:
    def __init__(self) -> None:
        self.induced: list[str] = []

    async def execute(self, ctx: RequestContext, *, recording_id: object, **_: object) -> object:
        self.induced.append(str(recording_id))
        return type("Understood", (), {"skill_id": f.skill().id})()


def _pursuit(
    uow: FakeUnitOfWork,
    *,
    capture: object = None,
    finish: object = None,
    understand: object = None,
) -> PursueGoal:
    return PursueGoal(
        uow,
        FakeCredentialVault(),
        FakeBrowserProvider(),
        None,
        None,
        FakeClock(),
        capture,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        finish,  # type: ignore[arg-type]
        understand,  # type: ignore[arg-type]
        egress_enabled=True,
    )


@pytest.mark.asyncio
async def test_a_deployment_without_a_vision_rung_says_so() -> None:
    """Rather than opening a browser and driving nothing at it."""
    with pytest.raises(VisionUnavailable, match="look at a screen"):
        await _pursuit(FakeUnitOfWork()).execute(
            CTX,
            goal=compose("create a transport mode", None),
            target_system="blue_yonder",
            values={},
        )


@pytest.mark.asyncio
async def test_a_pursuit_that_reached_its_goal_becomes_a_skill() -> None:
    capture, finish, understand = _Capture(), _Finish(), _Understand()
    pursuit = _pursuit(FakeUnitOfWork(), capture=capture, finish=finish, understand=understand)

    skill_id = await pursuit._keep(CTX, RecordingId("rec-1"), reached=True)

    assert capture.stopped == ["rec-1"]
    assert finish.sealed == ["rec-1"]
    assert understand.induced == ["rec-1"]
    assert skill_id


@pytest.mark.asyncio
async def test_a_pursuit_that_gave_up_teaches_nothing() -> None:
    """Half a form filled in is still a recording, and inducing from it would
    teach the wrong thing at full speed."""
    capture, finish, understand = _Capture(), _Finish(), _Understand()
    pursuit = _pursuit(FakeUnitOfWork(), capture=capture, finish=finish, understand=understand)

    skill_id = await pursuit._keep(CTX, RecordingId("rec-2"), reached=False)

    assert capture.stopped == ["rec-2"]
    assert finish.abandoned == [("rec-2", "the goal was not reached")]
    assert not understand.induced
    assert skill_id == ""
