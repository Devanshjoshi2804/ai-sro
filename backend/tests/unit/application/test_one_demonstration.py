"""A skill from a single demonstration, when the operator asks for one.

Two runs is the design: what differs between them is a parameter, what holds is
literal, and nothing is inferred. But a second demonstration is not always worth
what it costs -- a task done once a quarter, a screen an operator has already
walked through twice for a pair that induction refused -- and the answer to that
was previously "teach it again or have nothing".

So one is allowed, and it is honest about the price rather than hiding it: with
nothing to diff against, every value stays exactly as demonstrated and the skill
takes no parameters at all. It replays one specific act.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.induction.induce_skill import InduceSkill
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.execution.verdict import Verdict
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _taught(*, runs: int, writes: bool = False) -> Skill:
    uow = FakeUnitOfWork()
    ids = ("rec-a", "rec-b")[:runs]
    for recording_id, shipment in zip(ids, ("12345", "67890"), strict=False):
        recording = f.recording(frames=0, id=RecordingId(recording_id))
        recording.append_frame(
            f.frame(
                0,
                requests=(
                    f.request(
                        method="POST" if writes else "GET",
                        url=f"https://wms.test/api/shipments/{shipment}",
                    ),
                ),
            )
        )
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    await InduceSkill(
        uow,
        FakeClock(),
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())),
    ).execute(
        CTX,
        first=RecordingId("rec-a"),
        second=RecordingId("rec-b") if runs == 2 else None,
    )
    return next(iter(uow.skills.rows.values()))


async def test_one_demonstration_makes_a_skill_that_replays_it_exactly() -> None:
    skill = await _taught(runs=1)
    version = skill.versions[-1]

    assert version.steps, "the demonstration is the skill"
    assert version.parameters == (), "nothing varied, so nothing may be asked for"


async def test_a_skill_from_one_run_says_so_where_a_reviewer_will_see_it() -> None:
    """Provenance is what a supervisor reads before promoting anything. A
    version induced from one run and one induced from two are not the same kind
    of evidence, and the difference has to be legible without counting ids."""
    alone = (await _taught(runs=1)).versions[-1]
    paired = (await _taught(runs=2)).versions[-1]

    assert alone.provenance.recording_ids == (RecordingId("rec-a"),)
    assert "one demonstration" in alone.provenance.note
    assert len(paired.provenance.recording_ids) == 2
    assert "one demonstration" not in paired.provenance.note


async def test_two_runs_still_find_what_changed_between_them() -> None:
    """The single-run path must not cost the paired one anything."""
    paired = (await _taught(runs=2)).versions[-1]

    assert [p.name for p in paired.parameters], "a diff over two runs still parameterises"


async def test_an_unpaired_write_stops_at_shadow_until_somebody_says_otherwise() -> None:
    """Shadow produces the request and withholds it, which is exactly what a
    reviewer needs to see. Above that it is sent -- and every send is the same
    send, because one demonstration had nothing to diff against."""
    version = (await _taught(runs=1, writes=True)).versions[-1]
    assert version.stage is PromotionStage.SHADOW, "induction lands here"

    with pytest.raises(InvariantViolation, match="one demonstration"):
        version.promote(PromotionStage.ASSISTED, f.at(500), f.OPERATOR)

    version.promote(
        PromotionStage.ASSISTED, f.at(500), f.OPERATOR, acknowledging_fixed_values=True
    )
    assert version.stage is PromotionStage.ASSISTED


async def test_an_unpaired_read_climbs_like_anything_else() -> None:
    """Nothing is sent that changes anything, so there is nothing to acknowledge.
    Asking anyway teaches people to click past the question that matters."""
    version = (await _taught(runs=1, writes=False)).versions[-1]

    version.promote(PromotionStage.ASSISTED, f.at(500), f.OPERATOR)

    assert version.stage is PromotionStage.ASSISTED


async def test_two_demonstrations_are_never_asked_the_question() -> None:
    """The values a pair holds constant were held across two runs. That is
    evidence, not an accident of one."""
    version = (await _taught(runs=2, writes=True)).versions[-1]

    version.promote(PromotionStage.ASSISTED, f.at(500), f.OPERATOR)

    assert version.stage is PromotionStage.ASSISTED


async def test_a_clean_rehearsal_does_not_promote_an_unpaired_write_by_itself() -> None:
    """The ladder is climbed by evidence, and this is the rung where nobody is
    asked. A rehearsal proves the request can be built; it cannot prove that
    sending that exact request again is what anybody wants -- so the guard has
    to live on the earned path too, not only on the promotion by hand."""
    version = (await _taught(runs=1, writes=True)).versions[-1]
    assert version.stage is PromotionStage.SHADOW

    earned = version.earn(Verdict.WITHHELD, f.at(600))

    assert earned is None
    assert version.stage is PromotionStage.SHADOW


async def test_a_paired_write_still_earns_its_way_up() -> None:
    version = (await _taught(runs=2, writes=True)).versions[-1]

    assert version.earn(Verdict.WITHHELD, f.at(600)) is PromotionStage.ASSISTED
