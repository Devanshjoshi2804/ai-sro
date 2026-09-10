"""Where a run has got to, when some steps are done once per thing in a list.

The log is positional -- the first thing performed is position 0 -- and that is
what makes "has this already been done" answerable after a crash. A loop's body
occupies several positions, and how many is the length of a list the system
returns partway through, so the plan grows as the run learns it.
"""

from __future__ import annotations

from sro.application.execution.plan import next_step, total_positions
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.skill.loop import Binding, Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import Template
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def _version(*, looped: bool = True) -> object:
    return f.skill_version(
        steps=tuple(
            f.step(
                index=index,
                network_plan=f.network_plan(url=Template("https://wms.test/api/x"), body=None),
            )
            for index in range(3)
        ),
        parameters=(Parameter(name="line_id", kind=ParameterKind.ITERATED, source_step_index=0),),
        loops=(
            (
                Loop(
                    over_step_index=0,
                    over_pointer="/data/lines",
                    first_step=1,
                    last_step=1,
                    binds=(Binding(parameter="line_id", pointer="/lineId"),),
                ),
            )
            if looped
            else ()
        ),
    )


def _run() -> Run:
    return Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=f.skill().id,
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={"site": "DC01"},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
    )


def _did(run: Run, index: int, *, plan_step: int | None = None, iteration: int = 0) -> None:
    run.record(
        StepOutcome(
            index=index,
            plan_step=plan_step,
            iteration=iteration,
            medium=Medium.NETWORK,
            disposition=StepDisposition.PERFORMED,
            intent="did it",
        )
    )


def test_a_skill_with_no_loop_walks_its_steps_exactly_as_before() -> None:
    version, run = _version(looped=False), _run()

    assert next_step(version, run).step_index == 0
    _did(run, 0)
    assert next_step(version, run).step_index == 1
    _did(run, 1)
    _did(run, 2)
    assert next_step(version, run) is None
    assert total_positions(version, run) == 3


def test_the_body_is_walked_once_for_each_thing_in_the_list() -> None:
    version, run = _version(), _run()

    _did(run, 0)  # the step that produced the list
    run.will_iterate(1, [{"line_id": "7"}, {"line_id": "8"}, {"line_id": "9"}])

    seen = []
    for position in range(1, 5):
        nxt = next_step(version, run)
        assert nxt is not None
        seen.append((nxt.step_index, nxt.iteration, nxt.values.get("line_id")))
        _did(run, position, plan_step=nxt.step_index, iteration=nxt.iteration)

    assert seen == [(1, 0, "7"), (1, 1, "8"), (1, 2, "9"), (2, 0, None)]
    # And the run's own values are still there, beside the thing of the moment.
    assert next_step(version, run) is None
    assert total_positions(version, run) == 5


def test_a_run_that_stopped_mid_loop_resumes_where_it_stopped() -> None:
    """Which is the whole reason the log is positional: a worker that died
    between the second line and the third must not adjust the second again."""
    version, run = _version(), _run()
    _did(run, 0)
    run.will_iterate(1, [{"line_id": "7"}, {"line_id": "8"}, {"line_id": "9"}])
    _did(run, 1, plan_step=1, iteration=0)
    _did(run, 2, plan_step=1, iteration=1)

    nxt = next_step(version, run)

    assert nxt is not None
    assert (nxt.step_index, nxt.iteration, nxt.values["line_id"]) == (1, 2, "9")


def test_a_loop_whose_list_has_not_arrived_stops_rather_than_guessing() -> None:
    version, run = _version(), _run()
    _did(run, 0)

    # The step before the body answered without the list this loop needs. The
    # count is unknowable, and guessing one would be a warehouse doing something
    # a number of times nobody decided.
    assert next_step(version, run) is None


def test_a_list_with_nothing_in_it_skips_the_body_entirely() -> None:
    """Nothing was short-shipped. The task is done, and doing the body once
    with no line to act on would be a write built from nothing."""
    version, run = _version(), _run()
    _did(run, 0)
    run.will_iterate(1, [])

    nxt = next_step(version, run)

    assert nxt is not None
    assert nxt.step_index == 2, "the step after the loop"
