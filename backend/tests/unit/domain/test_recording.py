"""Recording aggregate: the guards that make provenance trustworthy."""

from __future__ import annotations

import pytest

from sro.domain.recording.artifact import ArtifactKind
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.recording import RecordingStatus
from sro.domain.shared.errors import InvariantViolation
from tests import factories as f


class TestFrameOrdering:
    def test_indices_are_assigned_by_the_aggregate_not_the_caller(self) -> None:
        rec = f.recording(frames=0)

        # A caller passing nonsense indices -- exactly what a retrying capture
        # adapter does -- must not be able to create gaps. The two-run diff
        # aligns runs positionally, so a gap silently mis-pairs steps.
        rec.append_frame(f.frame(index=99))
        rec.append_frame(f.frame(index=99))

        assert [frame.index for frame in rec.frames] == [0, 1]


class TestSealing:
    def test_sealed_recording_rejects_further_capture(self) -> None:
        rec = f.recording(frames=1, sealed=True)

        with pytest.raises(InvariantViolation, match="sealed"):
            rec.append_frame(f.frame())
        with pytest.raises(InvariantViolation, match="sealed"):
            rec.attach_artifact(f.artifact())

    def test_empty_recording_cannot_be_sealed(self) -> None:
        rec = f.recording(frames=0)

        with pytest.raises(InvariantViolation, match="no frames"):
            rec.seal(f.at(60))

    def test_empty_recording_can_be_abandoned(self) -> None:
        rec = f.recording(frames=0)

        rec.abandon(f.at(60), reason="operator closed the tab")

        assert rec.status is RecordingStatus.ABANDONED
        assert rec.abandon_reason == "operator closed the tab"

    def test_recording_cannot_end_before_it_started(self) -> None:
        rec = f.recording(frames=1)

        with pytest.raises(InvariantViolation, match="before it started"):
            rec.seal(f.at(-10))


class TestArtifacts:
    def test_narration_is_optional_and_detectable(self) -> None:
        rec = f.recording(frames=1)
        assert rec.has_narration is False

        rec.attach_artifact(f.artifact(ArtifactKind.AUDIO, content_type="audio/webm"))

        assert rec.has_narration is True

    def test_reattaching_replaces_rather_than_duplicating(self) -> None:
        rec = f.recording(frames=1)
        rec.attach_artifact(f.artifact(ArtifactKind.VIDEO, size_bytes=1))
        rec.attach_artifact(f.artifact(ArtifactKind.VIDEO, size_bytes=2))

        current = rec.artifact(ArtifactKind.VIDEO)
        assert current is not None
        assert current.size_bytes == 2


class TestPrimaryRequest:
    """A click fires analytics, prefetches and one real mutation. Picking the
    right one is what makes a network plan correct rather than merely present."""

    def test_prefers_the_successful_mutation_over_incidental_gets(self) -> None:
        beacon = f.request(request_id="a", method="GET", url="https://wms.test/telemetry")
        mutation = f.request(request_id="b", method="POST", started_at=f.at(11))
        frame = f.frame(requests=(beacon, mutation))

        assert frame.primary_request is mutation

    def test_falls_back_to_the_first_success_when_nothing_mutates(self) -> None:
        first = f.request(request_id="a", method="GET", started_at=f.at(10))
        second = f.request(request_id="b", method="GET", started_at=f.at(11))
        frame = f.frame(requests=(second, first))

        assert frame.primary_request is first

    def test_a_frame_with_no_traffic_has_no_primary_request(self) -> None:
        assert f.frame(requests=()).primary_request is None


class TestInputAction:
    def test_a_click_without_a_target_is_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="requires a target"):
            InputAction(kind=ActionKind.CLICK)

    def test_typing_without_a_value_is_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="requires a value"):
            InputAction(kind=ActionKind.TYPE, target=f.fingerprint())
