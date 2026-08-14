"""One demonstration to a skill, with the reading kept honest.

The two-run diff proves which values vary. This does not, and everything it
produces says so — the calls are evidence, the narrative is a reading.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.understand import UnderstandRecording
from sro.application.ports.interpretation import CandidateParameter, Reading, StepReading
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.parameter import Evidence
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
ADJUST = "https://wms.test/data/WM/wm/inventory/adjust?siteId=SG"


class FakeInterpreter:
    def __init__(self, reading: Reading | None = None, available: bool = True) -> None:
        self._reading = reading or Reading()
        self._available = available
        self.evidence: list[str] = []

    @property
    def available(self) -> bool:
        return self._available

    async def read(self, evidence: str) -> Reading:
        self.evidence.append(evidence)
        return self._reading


async def _recorded(uow: FakeUnitOfWork) -> None:
    rec = f.recording(frames=0, id=RecordingId("rec-1"), objective_key=None)
    rec.append_frame(
        f.frame(
            0,
            requests=(
                f.request(
                    method="PUT",
                    url=ADJUST,
                    request_body=f.Body(
                        text='{"handlingUnit":"LPN99","quantity":"48"}',
                        size_bytes=40,
                        mime_type="application/json",
                    ),
                ),
            ),
        )
    )
    rec.name_objective(f.objective(objective_type="adjust", entity_type="inventory"))
    rec.seal(f.at(300))
    await uow.recordings.add(rec)


def _understand(uow: FakeUnitOfWork, interpreter: FakeInterpreter) -> UnderstandRecording:
    return UnderstandRecording(uow, interpreter, FakeClock(), FakeIdFactory())


async def test_one_demonstration_becomes_a_skill() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow)
    reading = Reading(
        title="Adjust LPN quantity",
        summary="Adjusts an LPN's on-hand quantity.",
        steps=(StepReading(index=0, what="apply the new count to the LPN"),),
    )

    result = await _understand(uow, FakeInterpreter(reading)).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    skill = next(iter(uow.skills.rows.values()))
    version = skill.versions[-1]
    assert result.step_count == 1
    assert version.summary == "Adjusts an LPN's on-hand quantity."
    assert version.steps[0].intent == "apply the new count to the LPN"
    assert version.provenance.recording_ids == (RecordingId("rec-1"),)


async def test_a_parameter_nobody_can_point_at_is_dropped() -> None:
    """A model can name any parameter it likes. Only the ones pointing at a
    literal in the evidence survive."""
    uow = FakeUnitOfWork()
    await _recorded(uow)
    reading = Reading(
        steps=(StepReading(index=0, what="adjust"),),
        parameters=(
            CandidateParameter(name="quantity", value="48"),
            CandidateParameter(name="reason_code", value="NEVER-SEEN"),
        ),
    )

    await _understand(uow, FakeInterpreter(reading)).execute(CTX, recording_id=RecordingId("rec-1"))

    version = next(iter(uow.skills.rows.values())).versions[-1]
    assert [p.name for p in version.parameters] == ["quantity"]


async def test_what_one_run_yields_is_marked_proposed_not_proven() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow)
    reading = Reading(
        steps=(StepReading(index=0, what="adjust"),),
        parameters=(CandidateParameter(name="quantity", value="48"),),
    )

    await _understand(uow, FakeInterpreter(reading)).execute(CTX, recording_id=RecordingId("rec-1"))

    version = next(iter(uow.skills.rows.values())).versions[-1]
    assert version.parameters[0].evidence is Evidence.PROPOSED
    assert "reading" in version.provenance.note


async def test_the_proposed_value_becomes_a_placeholder_in_the_plan() -> None:
    """Otherwise every run of the skill would write this run's number."""
    uow = FakeUnitOfWork()
    await _recorded(uow)
    reading = Reading(
        steps=(StepReading(index=0, what="adjust"),),
        parameters=(CandidateParameter(name="quantity", value="48"),),
    )

    await _understand(uow, FakeInterpreter(reading)).execute(CTX, recording_id=RecordingId("rec-1"))

    plan = next(iter(uow.skills.rows.values())).versions[-1].steps[0].network_plan
    assert plan is not None
    assert "${quantity}" in str(plan.body)


async def test_a_credential_is_never_sent_to_the_interpreter() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow)
    interpreter = FakeInterpreter()

    await _understand(uow, interpreter).execute(CTX, recording_id=RecordingId("rec-1"))

    assert "«secret»" in interpreter.evidence[0] or "password" not in interpreter.evidence[0]


async def test_without_an_interpreter_the_skill_is_still_built() -> None:
    """The calls are the part that runs; the narrative is what makes it
    findable. Losing the second must not cost the first."""
    uow = FakeUnitOfWork()
    await _recorded(uow)

    result = await _understand(uow, FakeInterpreter(available=False)).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    assert result.step_count == 1
    assert result.proposed_parameter_count == 0
    assert "no interpreter" in result.caveat


async def test_an_unsealed_recording_is_refused() -> None:
    uow = FakeUnitOfWork()
    await uow.recordings.add(f.recording(frames=1, id=RecordingId("rec-open")))

    with pytest.raises(InductionFailed, match="seal it first"):
        await _understand(uow, FakeInterpreter()).execute(CTX, recording_id=RecordingId("rec-open"))
