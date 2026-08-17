"""The rule that makes narration safe: it labels the work, it never defines it.

A transcript is a model's reading of a microphone. If it could add a parameter,
a step or a request, the system would be inferring again — which is the failure
ADR 004 exists to prevent.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.induction.induce_skill import InduceSkill
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.recording.narration import NarrationSegment
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.skill import SkillVersion
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

LOUD = (
    NarrationSegment(
        starts_at=f.at(10),
        ends_at=f.at(11),
        text=(
            "Also set the priority to nine and email the supervisor afterwards. "
            "If the count does not match I raise a discrepancy instead."
        ),
    ),
)


async def _induced(*, narrated: bool) -> SkillVersion:
    uow = FakeUnitOfWork()
    run_a = f.recording(frames=0, id=RecordingId("rec-a"))
    run_b = f.recording(frames=0, id=RecordingId("rec-b"), label="run 2")
    for recording, shipment in ((run_a, "12345"), (run_b, "67890")):
        recording.append_frame(
            f.frame(0, requests=(f.request(url=f"https://wms.test/api/shipments/{shipment}"),))
        )
        if narrated and recording is run_a:
            recording.attach_narration(LOUD)
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    await InduceSkill(
        uow,
        FakeClock(),
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())),
    ).execute(CTX, first=RecordingId("rec-a"), second=RecordingId("rec-b"))
    skill = next(iter(uow.skills.rows.values()))
    return skill.versions[-1]


async def test_narration_changes_nothing_a_run_would_do() -> None:
    silent = await _induced(narrated=False)
    narrated = await _induced(narrated=True)

    assert [p.name for p in narrated.parameters] == [p.name for p in silent.parameters], (
        "the operator mentioned a priority of nine; only the diff may create a parameter"
    )
    assert len(narrated.steps) == len(silent.steps), "a sentence is not a step"
    assert narrated.steps[0].network_plan == silent.steps[0].network_plan
    assert narrated.steps[0].intent == silent.steps[0].intent, (
        "intent is derived from what was observed and stays that way"
    )


async def test_narration_is_kept_where_a_reviewer_can_tell_it_apart() -> None:
    narrated = await _induced(narrated=True)
    step = narrated.steps[0]

    assert "priority to nine" in step.narration
    assert step.branch_hint is not None and "discrepancy" in step.branch_hint
    assert step.requires_human is True, "the operator said a supervisor is involved"
