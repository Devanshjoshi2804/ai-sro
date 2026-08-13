"""Persistence must not quietly lose part of a capture.

The codec is derived from the domain's annotations, so the risk is not a
forgotten field but a type it cannot round-trip -- read-only mappings, frozen
sets of states, timezone-aware timestamps. Those are what these assert.
"""

from __future__ import annotations

from sro.domain.recording.network import Body, Initiator, InitiatorKind, StackFrame
from sro.infrastructure.db.codec import (
    dump_artifacts,
    dump_frames,
    dump_versions,
    load_artifacts,
    load_frames,
    load_versions,
)
from tests import factories as f


def test_a_frame_survives_a_round_trip_whole() -> None:
    request = f.request(
        request_body=Body(text='{"quantity": 12}', size_bytes=16),
        initiator=Initiator(
            kind=InitiatorKind.SCRIPT,
            stack=(
                StackFrame(function="onRelease", url="https://wms.test/a.js", line=4, column=1),
            ),
        ),
    )
    frames = (f.frame(requests=(request,)),)

    restored = load_frames(dump_frames(frames))

    assert restored == frames


def test_headers_and_bodies_come_back_verbatim() -> None:
    frames = (f.frame(requests=(f.request(),)),)

    restored = load_frames(dump_frames(frames))
    original_headers = frames[0].requests[0].request_headers

    assert dict(restored[0].requests[0].request_headers) == dict(original_headers)
    assert "Authorization" in restored[0].requests[0].request_headers


def test_artifacts_round_trip() -> None:
    artifacts = (f.artifact(),)

    assert load_artifacts(dump_artifacts(artifacts)) == artifacts


def test_a_skill_version_round_trips_with_its_provenance() -> None:
    versions = (f.skill_version(),)

    restored = load_versions(dump_versions(versions))

    assert restored[0].steps == versions[0].steps
    assert restored[0].parameters == versions[0].parameters
    assert restored[0].provenance == versions[0].provenance
    assert restored[0].stage is versions[0].stage
