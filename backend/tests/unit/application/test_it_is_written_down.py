"""Whether what a use case changed was actually written.

The fakes hold the same objects the use case mutated, so a test asserting on
the aggregate it got back proves the code changed an object in memory and
nothing more. A use case that forgot to save, or saved and never committed,
passed the whole suite -- and the fault would first appear as a promotion that
disappeared when the API restarted.

Commit counting is what the fast tests can honestly check. That transactions
hold is proved in ``tests/integration`` against Postgres.
"""

from __future__ import annotations

from sro.application.connection.browsers import Browsers
from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.recording.start_recording import StartRecording
from sro.application.skill.promote_skill import PromoteSkill
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def test_a_promotion_is_committed() -> None:
    uow = FakeUnitOfWork()
    skill = f.skill(versions=1)
    await uow.skills.add(skill)

    await PromoteSkill(uow, FakeClock()).execute(
        CTX, skill_id=skill.id, version=1, to=PromotionStage.SHADOW
    )

    assert uow.commits >= 1, "the rung it moved to would not survive a restart"


async def test_a_started_recording_is_committed() -> None:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    browsers = Browsers(browser, uow, clock, FakeIdFactory())

    await StartRecording(uow, browser, clock, FakeIdFactory(), browsers).execute(CTX, label="run 1")

    assert uow.commits >= 1, "a demonstration nothing wrote down has no frames to collect"


async def test_a_recorded_claim_is_committed() -> None:
    uow = FakeUnitOfWork()

    claim = Claim(
        system="blue_yonder",
        kind=EntryKind.ENDPOINT,
        key="/data/WM/wm/suppliers",
        title="suppliers (collection)",
        body={"status": "unknown"},
        source="index/api-endpoints.json",
        evidence=EvidenceLevel.ASSERTED,
    )

    await RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()).execute(CTX, (claim,))

    assert uow.commits >= 1
