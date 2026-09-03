"""A value changed while the run is still going.

The panel shows a run as it happens, one row per step, and a step that has not
been sent yet can still be argued with: the operator picked the wrong address,
or the mail did not say which one. What has already gone to the warehouse has
gone; what is still to come uses the new value.

The change is recorded rather than merely applied. "Who decided this run would
use A000221" is the first question about a run that wrote the wrong thing, and
the answer has to be on the run itself.
"""

from __future__ import annotations

import pytest

from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    StepDisposition,
    StepOutcome,
)
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def _running() -> Run:
    return Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={"address": "A000144886", "name": "Acme"},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
        target_system="blue_yonder",
    )


def test_a_running_run_takes_a_new_value_for_what_is_still_to_come() -> None:
    run = _running()

    run.revise({"address": "A000221"}, at=f.at(5))

    assert run.parameters["address"] == "A000221"
    assert run.parameters["name"] == "Acme", "what nobody changed is left alone"


def test_a_change_is_recorded_as_somebody_deciding_it() -> None:
    """Not just applied. A run that wrote the wrong thing is read afterwards,
    and "the operator changed this at 12:07" is the answer it has to hold."""
    run = _running()

    run.revise({"address": "A000221"}, at=f.at(5))

    assert run.revisions == (("address", "A000221", f.at(5)),)


def test_a_name_the_run_never_had_is_refused() -> None:
    """A skill's parameters are what its steps render. A name outside them
    reaches nothing, so accepting it would be recording a decision that has no
    effect -- which reads, later, as a change that was made and ignored."""
    run = _running()

    with pytest.raises(InvariantViolation, match="no parameter named colour"):
        run.revise({"colour": "red"}, at=f.at(5))

    assert run.revisions == ()


def test_a_finished_run_cannot_be_revised() -> None:
    run = _running()
    run.record(
        StepOutcome(
            index=0,
            medium=Medium.NETWORK,
            disposition=StepDisposition.PERFORMED,
            intent="save",
            status_code=200,
        )
    )
    run.finish(f.at(9))

    with pytest.raises(InvariantViolation, match="cannot be added to"):
        run.revise({"address": "A000221"}, at=f.at(10))


def test_revising_nothing_is_refused() -> None:
    """An empty change is a press that did nothing, and a run carrying a
    revision of nothing says somebody decided something when they did not."""
    run = _running()

    with pytest.raises(InvariantViolation, match="names no value"):
        run.revise({}, at=f.at(5))
