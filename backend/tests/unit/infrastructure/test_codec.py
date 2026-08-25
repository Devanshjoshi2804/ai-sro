"""Persistence must not quietly lose part of a capture.

The codec is derived from the domain's annotations, so the risk is not a
forgotten field but a type it cannot round-trip -- read-only mappings, frozen
sets of states, timezone-aware timestamps. Those are what these assert.
"""

from __future__ import annotations

from sro.domain.recording.network import Body, Initiator, InitiatorKind, StackFrame
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.transform import Transform
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


def test_what_was_done_to_a_derived_value_comes_back_with_it() -> None:
    """A skill version is a JSONB document, so a field the codec cannot carry is
    a field that silently becomes `None` on the next read -- and a transformation
    that disappears sends `77` where the demonstration proved `LPN-00077`."""
    versions = (
        f.skill_version(
            steps=(f.step(index=0, network_plan=None), f.step(index=1)),
            parameters=(
                Parameter(
                    name="shipment_id",
                    kind=ParameterKind.DERIVED,
                    source_step_index=0,
                    source_pointer="/data/waveId",
                    transform=Transform(ops=(("pad", "5", "0"), ("prefix", "LPN-"))),
                ),
            ),
        ),
    )

    restored = load_versions(dump_versions(versions))

    carried = restored[0].parameters[0].transform
    assert carried is not None
    assert carried.apply("77") == "LPN-00077"
