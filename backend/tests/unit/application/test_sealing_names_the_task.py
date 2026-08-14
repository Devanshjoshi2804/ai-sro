"""Sealing is where a demonstration says what it was, because by then it has."""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.recording.finish_recording import FinishRecording, UnnamedDemonstration
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.shared.identifiers import RecordingId
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider, FakeClock, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
ADJUST = "https://wms-qa.jdadelivers.com/data/WM/wm/inventory/adjust?siteId=SG"


async def _sealed(*, connected: bool = False, url: str = ADJUST) -> object:
    uow = FakeUnitOfWork()
    recording = f.recording(frames=0, objective_key=None)
    recording.append_frame(f.frame(0, requests=(f.request(method="PUT", url=url),)))
    await uow.recordings.add(recording)

    if connected:
        await uow.connections.add(
            Connection(
                id=ConnectionId("conn-1"),
                tenant_id=f.TENANT,
                name="Blue Yonder QA",
                target_system="blue_yonder",
                base_url="https://wms-qa.jdadelivers.com/",
                created_at=f.T0,
            )
        )

    finish = FinishRecording(uow, FakeBrowserProvider(), FakeClock())
    return await finish.seal(CTX, recording_id=RecordingId("rec-1"))


async def test_a_demonstration_names_itself_from_the_call_it_ended_on() -> None:
    recording = await _sealed()

    assert recording.objective_key is not None
    assert recording.objective_key.entity_type == "inventory"
    assert recording.objective_key.objective_type == "adjust"
    assert recording.objective_key.facility == "SG"


async def test_the_connected_system_names_the_system_rather_than_the_hostname() -> None:
    recording = await _sealed(connected=True)

    assert recording.objective_key is not None
    assert recording.objective_key.target_system == "blue_yonder", (
        "the vault scope and the knowledge base both use the name the operator connected under"
    )


async def test_a_demonstration_that_asked_the_server_nothing_asks_the_operator() -> None:
    uow = FakeUnitOfWork()
    recording = f.recording(frames=0, objective_key=None)
    recording.append_frame(
        f.frame(0, action=InputAction(kind=ActionKind.SCROLL), requests=(), ax_graph=None)
    )
    await uow.recordings.add(recording)

    with pytest.raises(UnnamedDemonstration):
        await FinishRecording(uow, FakeBrowserProvider(), FakeClock()).seal(
            CTX, recording_id=RecordingId("rec-1")
        )


async def test_the_second_run_of_a_pair_is_sealed_under_the_first_run_s_name() -> None:
    uow = FakeUnitOfWork()
    recording = f.recording(frames=0, objective_key=None)
    recording.append_frame(f.frame(0, requests=(f.request(method="PUT", url=ADJUST),)))
    await uow.recordings.add(recording)

    sealed = await FinishRecording(uow, FakeBrowserProvider(), FakeClock()).seal(
        CTX, recording_id=RecordingId("rec-1"), objective_key=f.objective()
    )

    assert sealed.objective_key == f.objective(), "an explicit key is not second-guessed"
