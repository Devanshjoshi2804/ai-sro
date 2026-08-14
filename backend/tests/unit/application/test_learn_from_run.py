"""What a run teaches the store, and what it is not allowed to teach it."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _run(*outcomes: StepOutcome, finished: bool = True) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
    )
    for outcome in outcomes:
        run.record(outcome)
    if finished:
        run.finish(f.at(60))
    return run


def _outcome(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 0,
        "medium": Medium.NETWORK,
        "disposition": StepDisposition.PERFORMED,
        "intent": "adjust the count",
        "method": "PUT",
        "url": "https://wms.test/data/WM/wm/inventory/adjust?siteId=SG",
        "status_code": 200,
    }
    return StepOutcome(**{**defaults, **overrides})  # type: ignore[arg-type]


async def _learn(run: Run, uow: FakeUnitOfWork) -> None:
    record = RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())
    await LearnFromRun(record).execute(CTX, run=run, system="blue_yonder")


async def test_a_verified_call_becomes_something_the_store_knows() -> None:
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome()), uow)

    entry = await uow.knowledge.current(
        f.TENANT,
        system="blue_yonder",
        kind=EntryKind.STATUS,
        key="PUT /data/WM/wm/inventory/adjust",
    )
    assert entry is not None
    assert entry.body["status"] == 200
    assert entry.source == "run-1", "the claim cites the run that proved it"
    assert entry.evidence is EvidenceLevel.REPRODUCED, (
        "the call was made and checked; nothing was created, read back and deleted"
    )


async def test_a_withheld_shadow_write_teaches_nothing() -> None:
    """It was built and never sent. Its status is unknown, not good."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome(disposition=StepDisposition.WITHHELD, status_code=None)), uow)

    assert uow.knowledge.rows == {}


async def test_a_step_whose_assertions_failed_teaches_nothing() -> None:
    """The skill and the system disagree. Recording that would teach the store
    the skill's bugs as facts about the WMS."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome(assertion_failures=("/data/ok is 'false'",))), uow)

    assert uow.knowledge.rows == {}


async def test_a_run_that_did_not_succeed_teaches_nothing() -> None:
    uow = FakeUnitOfWork()
    run = _run(_outcome(disposition=StepDisposition.FAILED, status_code=500), finished=True)
    assert run.status is RunStatus.FAILED

    await _learn(run, uow)

    assert uow.knowledge.rows == {}


async def test_the_url_is_recorded_without_its_parameters() -> None:
    """The path is the fact; `siteId=SG` is this run's parameter, and keying on
    it would make one endpoint look like a hundred."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome()), uow)

    entry = next(iter(uow.knowledge.rows.values()))
    assert "?" not in entry.key
    assert entry.body["path"] == "/data/WM/wm/inventory/adjust"
