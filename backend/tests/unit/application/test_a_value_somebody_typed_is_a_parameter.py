"""One demonstration, and the box the operator filled in.

A single run cannot disagree with itself, so everything it sent looks equally
fixed -- including the supplier code somebody had just typed. Replaying that
literal creates the same supplier again, which is the whole failure this exists
to prevent. The two-run path already recovers these; this is the path a mined
candidate takes, and it did not.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.induction.understand import UnderstandRecording
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.parameter import ParameterKind
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
TYPED = "ACME-2"


async def _demonstration(uow: FakeUnitOfWork) -> None:
    """Type a supplier code into a box, then save it."""
    recording = f.recording(frames=0)
    recording.append_frame(
        f.frame(
            index=0,
            action=InputAction(
                kind=ActionKind.TYPE,
                target=f.fingerprint(role="textbox", accessible_name="Supplier code"),
                value=TYPED,
            ),
            requests=(
                f.request(
                    method="POST",
                    url="https://wms.test/api/suppliers",
                    request_body=Body(
                        text=f'{{"code": "{TYPED}", "status": "active"}}',
                        size_bytes=40,
                        mime_type="application/json",
                    ),
                ),
            ),
        )
    )
    recording.seal(f.at(600))
    await uow.recordings.add(recording)


async def test_the_value_becomes_a_parameter_with_no_model_involved() -> None:
    uow = FakeUnitOfWork()
    await _demonstration(uow)

    await UnderstandRecording(uow, NoInterpreter(), FakeClock(), FakeIdFactory()).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    version = next(iter(uow.skills.rows.values())).versions[-1]
    typed = [p for p in version.parameters if p.kind is ParameterKind.INPUT]
    assert [p.observed_values for p in typed] == [(TYPED,)]


async def test_the_plan_carries_a_placeholder_rather_than_that_run_s_literal() -> None:
    # Otherwise every run of this skill creates ACME-2 again.
    uow = FakeUnitOfWork()
    await _demonstration(uow)

    await UnderstandRecording(uow, NoInterpreter(), FakeClock(), FakeIdFactory()).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    version = next(iter(uow.skills.rows.values())).versions[-1]
    plan = version.steps[0].network_plan
    assert plan is not None
    assert plan.body is not None
    assert TYPED not in plan.body.raw
    assert version.parameters[0].name in plan.placeholders


async def test_a_credential_the_operator_typed_never_becomes_a_parameter() -> None:
    # The recorder drops the value at source; nothing downstream may reinstate
    # it, and a password-shaped placeholder in a plan is a plan that asks for one.
    uow = FakeUnitOfWork()
    recording = f.recording(frames=0)
    recording.append_frame(
        f.frame(
            index=0,
            action=InputAction(
                kind=ActionKind.TYPE,
                target=f.fingerprint(role="textbox", accessible_name="Password"),
                value=None,
                secret=True,
            ),
        )
    )
    recording.seal(f.at(600))
    await uow.recordings.add(recording)

    await UnderstandRecording(uow, NoInterpreter(), FakeClock(), FakeIdFactory()).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    version = next(iter(uow.skills.rows.values())).versions[-1]
    assert version.parameters == ()
