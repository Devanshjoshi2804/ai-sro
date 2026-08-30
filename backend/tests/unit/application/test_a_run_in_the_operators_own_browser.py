"""A run performed in the browser the operator is sitting in front of.

What has to hold: a run bound to a device uses that device, and a run bound to a
device that cannot be reached does not quietly use the deployment's own browser
instead. That one is signed in as somebody else, on a screen nobody
demonstrated, and it is the failure mode this whole seam exists to prevent.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    ExecutionRequest,
    StartRun,
)
from sro.application.execution.stops import Stops
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeAgentDrivers,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUiDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
LAPTOP = DeviceId("dev-1")

FINDABLE = f.ui_plan(
    locators=(
        ControlLocator(
            strategy=LocatorStrategy.COMPONENT, query=Template("panel#waves button#release")
        ),
    )
)


async def _assisted_skill(uow: FakeUnitOfWork) -> None:
    skill = f.skill(versions=0)
    version = f.skill_version(steps=(f.step(ui_plan=FINDABLE),))
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(800), f.OPERATOR)
    await uow.skills.add(skill)


async def _run(uow: FakeUnitOfWork, *, medium: Medium, device: DeviceId | None) -> Run:
    return await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=f.skill().id,
            parameters={"shipment_id": "12345"},
            medium=medium,
            device_id=device,
            authorized_by=str(f.OPERATOR),
        ),
    )


async def test_a_gesture_goes_to_the_device_the_run_named() -> None:
    uow, agents, server = FakeUnitOfWork(), FakeAgentDrivers(), FakeUiDriver()
    await _assisted_skill(uow)
    run = await _run(uow, medium=Medium.UI, device=LAPTOP)

    outcome = await ExecuteStep(
        uow, FakeHttpCaller(), FakeCredentialVault(), server, agents=agents
    ).execute(CTX, run_id=run.id, index=0)

    assert outcome.disposition is StepDisposition.PERFORMED
    assert agents.asked_for == [(str(f.TENANT), "dev-1")]
    assert server.asked == [], "the deployment's own browser was driven instead"


async def test_a_call_in_a_device_run_goes_out_of_the_operators_page() -> None:
    # Which is the point of it: the request carries their session, so a skill
    # runs against a system this deployment holds no credentials for.
    uow, agents = FakeUnitOfWork(), FakeAgentDrivers()
    server_caller = FakeHttpCaller()
    await _assisted_skill(uow)
    run = await _run(uow, medium=Medium.NETWORK, device=LAPTOP)

    await ExecuteStep(uow, server_caller, FakeCredentialVault(), agents=agents).execute(
        CTX, run_id=run.id, index=0
    )

    assert agents.asked_for == [(str(f.TENANT), "dev-1")]
    assert server_caller.sent == []


async def test_a_device_run_with_no_channel_open_does_not_fall_back_to_our_browser() -> None:
    uow, server = FakeUnitOfWork(), FakeUiDriver()
    await _assisted_skill(uow)
    run = await _run(uow, medium=Medium.UI, device=LAPTOP)

    outcome = await ExecuteStep(
        uow, FakeHttpCaller(), FakeCredentialVault(), server, agents=None
    ).execute(CTX, run_id=run.id, index=0)

    assert outcome.disposition is StepDisposition.FAILED
    assert "no browser" in (outcome.detail or "")
    assert server.asked == []


async def test_a_call_in_a_device_run_is_never_sent_from_the_server_instead() -> None:
    uow, server_caller = FakeUnitOfWork(), FakeHttpCaller()
    await _assisted_skill(uow)
    run = await _run(uow, medium=Medium.NETWORK, device=LAPTOP)

    outcome = await ExecuteStep(uow, server_caller, FakeCredentialVault(), agents=None).execute(
        CTX, run_id=run.id, index=0
    )

    assert outcome.disposition is StepDisposition.FAILED
    assert server_caller.sent == []


async def test_a_run_naming_no_device_is_performed_where_it_always_was() -> None:
    uow, agents, server = FakeUnitOfWork(), FakeAgentDrivers(), FakeUiDriver()
    await _assisted_skill(uow)
    run = await _run(uow, medium=Medium.UI, device=None)

    await ExecuteStep(uow, FakeHttpCaller(), FakeCredentialVault(), server, agents=agents).execute(
        CTX, run_id=run.id, index=0
    )

    assert agents.asked_for == []
    assert server.asked != []


async def test_the_device_is_on_the_run_so_the_record_says_which_browser() -> None:
    uow = FakeUnitOfWork()
    await _assisted_skill(uow)

    run = await _run(uow, medium=Medium.UI, device=LAPTOP)

    assert run.device_id == LAPTOP


@pytest.mark.parametrize("medium", [Medium.UI, Medium.NETWORK])
async def test_a_shadow_run_in_somebodys_browser_still_withholds_its_writes(
    medium: Medium,
) -> None:
    """The rule does not soften because the browser belongs to the operator: a
    click is indistinguishable from a call once it has happened."""
    uow, agents = FakeUnitOfWork(), FakeAgentDrivers()
    skill = f.skill(versions=0)
    version = f.skill_version(steps=(f.step(ui_plan=FINDABLE),))
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=skill.id,
            parameters={"shipment_id": "12345"},
            medium=medium,
            device_id=LAPTOP,
        ),
    )

    outcome = await ExecuteStep(
        uow, FakeHttpCaller(), FakeCredentialVault(), FakeUiDriver(), agents=agents
    ).execute(CTX, run_id=run.id, index=0)

    assert outcome.disposition is StepDisposition.WITHHELD
    assert agents.asked_for == []


async def test_a_stopped_run_says_a_person_stopped_it_rather_than_that_it_failed_a_check() -> None:
    """Both are FAILED, and a reviewer has to be able to tell them apart.

    A run that failed its post-conditions is the skill being wrong. A run
    somebody stopped is a person changing their mind, and reading the second as
    the first is how a working skill gets distrusted.
    """
    uow, agents = FakeUnitOfWork(), FakeAgentDrivers()
    await _assisted_skill(uow)
    stops = Stops()
    executor = ExecuteSkill(
        uow,
        FakeHttpCaller(),
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        FakeUiDriver(),
        agents=agents,
        stops=stops,
    )

    started = await executor.begin(
        CTX,
        ExecutionRequest(
            skill_id=f.skill().id,
            parameters={"shipment_id": "12345"},
            medium=Medium.UI,
            device_id=LAPTOP,
            authorized_by=str(f.OPERATOR),
        ),
    )
    # Asked before the first step, so nothing is sent at all -- which is the
    # only moment a stop can be honoured without a warehouse having been
    # touched.
    stops.ask(started.id)
    finished = await executor.resume(CTX, started)

    assert finished.status is RunStatus.FAILED
    assert finished.failure == "a person stopped this run"
    assert list(finished.steps) == []


async def test_a_run_nobody_stopped_is_not_treated_as_stopped() -> None:
    """The set is cleared when a run ends, and a run id is never reused -- but a
    stale entry would end the next run before its first step."""
    uow, agents = FakeUnitOfWork(), FakeAgentDrivers()
    await _assisted_skill(uow)
    stops = Stops()
    executor = ExecuteSkill(
        uow,
        FakeHttpCaller(),
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        FakeUiDriver(),
        agents=agents,
        stops=stops,
    )

    request = ExecutionRequest(
        skill_id=f.skill().id,
        parameters={"shipment_id": "12345"},
        medium=Medium.UI,
        device_id=LAPTOP,
        authorized_by=str(f.OPERATOR),
    )
    first = await executor.begin(CTX, request)
    stops.ask(first.id)
    await executor.resume(CTX, first)

    assert not stops.asked(first.id), "the stop outlived the run it was for"
