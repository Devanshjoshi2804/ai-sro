"""Capture is drained on an interval; causality is not.

A response that finishes just after a drain arrives in the next batch, with no
input event in front of it. Discarding it costs that step the very call a skill
would replay, so it has to reach the frame it belongs to.
"""

from __future__ import annotations

from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent
from sro.application.context import RequestContext
from sro.application.recording.ingest_capture_events import IngestCaptureEvents, IngestResult
from sro.domain.shared.identifiers import RecordingId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _ingest(
    uow: FakeUnitOfWork, recording_id: RecordingId, events: list[CaptureEvent]
) -> IngestResult:
    return await IngestCaptureEvents(uow).execute(CTX, recording_id=recording_id, events=events)


class TestLateEvidence:
    async def test_a_call_arriving_after_the_drain_reaches_its_click(self) -> None:
        uow = FakeUnitOfWork()
        recording = f.recording(frames=0)
        await uow.recordings.add(recording)

        click = InputEvent(at=f.at(10), action=f.frame().action)
        await _ingest(uow, recording.id, [click])

        # Next drain: the POST the click caused, alone.
        late = RequestEvent(request=f.request(request_id="late", started_at=f.at(11)))
        result = await _ingest(uow, recording.id, [late])

        stored = await uow.recordings.get(f.TENANT, recording.id)
        assert len(stored.frames) == 1, "a late call must not open a frame of its own"
        assert [r.request_id for r in stored.frames[0].requests] == ["late"]
        assert result.absorbed_requests == 1
        assert result.orphaned_requests == 0

    async def test_traffic_before_any_action_is_still_reported_as_orphaned(self) -> None:
        uow = FakeUnitOfWork()
        recording = f.recording(frames=0)
        await uow.recordings.add(recording)

        result = await _ingest(
            uow, recording.id, [RequestEvent(request=f.request(request_id="page-load"))]
        )

        stored = await uow.recordings.get(f.TENANT, recording.id)
        assert stored.frames == ()
        assert result.orphaned_requests == 1
        assert result.absorbed_requests == 0

    async def test_absorbing_does_not_disturb_the_frame_it_lands_on(self) -> None:
        uow = FakeUnitOfWork()
        recording = f.recording(frames=0)
        await uow.recordings.add(recording)
        await _ingest(uow, recording.id, [InputEvent(at=f.at(10), action=f.frame().action)])
        await _ingest(uow, recording.id, [RequestEvent(request=f.request(request_id="late"))])

        stored = await uow.recordings.get(f.TENANT, recording.id)
        frame = stored.frames[0]

        assert frame.index == 0
        assert frame.occurred_at == f.at(10)
        assert frame.action.kind is f.frame().action.kind
