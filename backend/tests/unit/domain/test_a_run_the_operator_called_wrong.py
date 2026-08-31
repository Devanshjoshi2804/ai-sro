"""A run whose steps were perfect and whose result was wrong.

`judge` reads statuses, media and escalations. Every one of them can be clean
while the record the run created is not the one anybody wanted -- a work
operation with the priority off by a digit is a successful run and a wrong
answer. That is the one failure the ladder cannot see, and the only witness is
the person whose browser it ran in.
"""

from __future__ import annotations

from pytest import raises

from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.execution.verdict import Verdict, judge
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def _run(*outcomes: StepOutcome, stage: PromotionStage = PromotionStage.ASSISTED) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=stage,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
        target_system="blue_yonder",
    )
    for outcome in outcomes:
        run.record(outcome)
    run.finish(f.at(60))
    return run


def _step(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 0,
        "medium": Medium.NETWORK,
        "disposition": StepDisposition.PERFORMED,
        "intent": "adjust",
        "status_code": 200,
    }
    return StepOutcome(**{**defaults, **overrides})  # type: ignore[arg-type]


def _clean_run() -> Run:
    """A run that `judge` calls CLEAN: succeeded, every step a network call."""
    return _run(_step())


def test_a_run_the_operator_called_wrong_is_a_failure_however_clean_its_steps() -> None:
    run = _clean_run()
    assert judge(run) is Verdict.CLEAN

    run.called_wrong("undone by the operator")

    assert judge(run) is Verdict.FAILED


def test_a_run_nobody_touched_is_judged_exactly_as_before() -> None:
    """Silence is not a verdict. Nothing is asked after a run, so nothing goes
    unanswered, and a run the operator ignored must not drift downwards for it."""
    assert judge(_clean_run()) is Verdict.CLEAN


def test_the_reason_is_kept_because_undone_and_mistyped_are_different_things() -> None:
    run = _clean_run()
    run.called_wrong("wrong priority")
    assert run.wrong_because == "wrong priority"


def test_a_run_cannot_be_called_wrong_twice_with_a_different_story() -> None:
    """The first answer is the one the operator gave while they were looking at
    it. A second, later, is somebody rewriting the record."""
    run = _clean_run()
    run.called_wrong("undone by the operator")
    with raises(InvariantViolation, match="already"):
        run.called_wrong("actually it was fine")
