"""Whether the panel may offer to take back what a run just made.

A visible undo is the strongest trust mechanism an agentic surface has, because
trust is knowing you can recover. It is also the one place this design could
most easily start guessing, so it does not: three facts or no button.
"""

from __future__ import annotations

from sro.application.execution.reversal import reversal_for
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill
from sro.domain.skill.template import Template
from tests import factories as f


def _run(*outcomes: StepOutcome, learned: dict[str, str] | None = None) -> Run:
    """A finished run, following the pattern in test_autonomy.py: recorded,
    then learned, then finished -- the order a real run actually goes in."""
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
        target_system="wms",
    )
    for outcome in outcomes:
        run.record(outcome)
    for name, value in (learned or {}).items():
        run.learn(name, value)
    run.finish(f.at(60))
    return run


def _step(index: int, method: str, url: str, status: int = 200) -> StepOutcome:
    return StepOutcome(
        index=index,
        medium=Medium.NETWORK,
        disposition=StepDisposition.PERFORMED,
        intent="do the thing",
        method=method,
        url=url,
        status_code=status,
    )


def _run_that_created(identifier: str | None) -> Run:
    """A run whose write was POST /api/workOperations, having read back an id."""
    outcome = _step(0, "POST", "https://wms.test/api/workOperations")
    learned = {"operation_id": identifier} if identifier is not None else {}
    return _run(outcome, learned=learned)


def _deletes(path: str, *, stage: PromotionStage = PromotionStage.ASSISTED) -> Skill:
    """A skill whose only step is a DELETE on that path, promoted to `stage`."""
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=NetworkPlan(
                    method="DELETE",
                    url=Template(path),
                    body=None,
                    expected_status=204,
                ),
                ui_plan=None,
            ),
        ),
        parameters=(f.parameter(name="operation_id", observed_values=("NDPCK",)),),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    if stage is PromotionStage.ASSISTED:
        # A fresh version starts at RECORDED, which is not runnable; every test
        # here but one wants a skill the executor would actually perform.
        version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR)
        version.promote(PromotionStage.ASSISTED, f.at(20), f.OPERATOR)
    return skill


def test_an_undo_is_offered_when_all_three_facts_hold() -> None:
    found = reversal_for(
        _run_that_created("NDPCK"),
        [_deletes("https://wms.test/api/workOperations/$operation_id")],
    )

    assert found is not None
    assert found.parameters == {"operation_id": "NDPCK"}


def test_nothing_is_offered_when_the_run_never_learned_what_it_made() -> None:
    """A button that cannot name what it would remove is worse than no button."""
    assert (
        reversal_for(
            _run_that_created(None),
            [_deletes("https://wms.test/api/workOperations/$operation_id")],
        )
        is None
    )


def test_a_delete_on_another_resource_is_not_an_undo() -> None:
    """Shapes are compared, not words. `workAreas` is not `workOperations`, and
    a model's opinion that they look similar is exactly what this refuses."""
    assert (
        reversal_for(
            _run_that_created("NDPCK"),
            [_deletes("https://wms.test/api/workAreas/$operation_id")],
        )
        is None
    )


def test_a_skill_that_may_not_run_is_not_an_undo() -> None:
    """Offering it would put a button in front of somebody that the executor
    then refuses, which teaches them the panel lies."""
    recorded = _deletes(
        "https://wms.test/api/workOperations/$operation_id",
        stage=PromotionStage.RECORDED,
    )

    assert reversal_for(_run_that_created("NDPCK"), [recorded]) is None


def test_a_run_that_only_read_has_nothing_to_take_back() -> None:
    run = _run(_step(0, "GET", "https://wms.test/api/workOperations"))

    assert (
        reversal_for(run, [_deletes("https://wms.test/api/workOperations/$operation_id")]) is None
    )
