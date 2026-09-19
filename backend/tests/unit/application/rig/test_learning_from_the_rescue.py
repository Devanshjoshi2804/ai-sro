"""The pass that takes the operator's own repair as the lesson for a step.

`sro.domain.execution.rescued` holds the rule and the argument; these are the
three things the pass around it can get wrong -- which run it reads, which step
of the JOB that run's failed row was, and how far back it looks.

The end-to-end shape is in `test_runner.py`:
`test_a_step_the_operator_fixed_by_hand_is_what_the_next_run_tries`.
"""

from __future__ import annotations

from sro.application.execution.learn_from_rescue import learn_from_the_rescue
from sro.domain.execution.rescued import K_SOON
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("greyorange")
WMS = "http://127.0.0.1:63319"
FINISHED = 1_000_000.0

JOB = Workflow(
    id="wfl_1",
    tenant=TENANT.value,
    title="Delete a Customer Type",
    narrative="n",
    steps=[
        Step(order=0, says="Opens the filter dropdown", system=None, cites=["g-demo"]),
        Step(order=1, says="Presses delete", system=None, cites=["g-demo-2"]),
    ],
)

DEMONSTRATED = {
    "g-demo": Target(test_id="filter-btn"),
    "g-demo-2": Target(test_id="delete-btn"),
}


def _gesture(gesture_id: str, at: float, target: Target) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=TENANT.value,
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{WMS}/customerTypes",
        system=WMS,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at, target=target),
    )


BY_HAND = _gesture(
    "g-by-hand", FINISHED + 4.0, Target(role="button", name="Filter", css_path="div > button")
)


def _run(*steps: RunStep, finished_at: str = "2026-09-19T10:00:00+00:00") -> WorkflowRun:
    return WorkflowRun(
        id="run_1",
        tenant=TENANT.value,
        workflow_id=JOB.id,
        device_id="dev",
        values={},
        started_by="form",
        live=True,
        allow_focus=True,
        started_at="2026-09-19T09:59:00+00:00",
        finished_at=finished_at,
        outcome="failed",
        steps=list(steps),
    )


def _failed(order: int, of_step: int) -> RunStep:
    return RunStep(
        order=order,
        says="Opens the filter dropdown",
        verdict="failed",
        of_step=of_step,
        before_url=f"{WMS}/customerTypes",
    )


def _held(order: int, of_step: int) -> RunStep:
    return RunStep(
        order=order,
        says="held",
        verdict="held",
        of_step=of_step,
        before_url=f"{WMS}/customerTypes",
    )


async def _uow(run: WorkflowRun, *gestures: Gesture) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.workflows.save(JOB)
    await uow.workflow_runs.save(run)
    if gestures:
        await uow.gestures.add_gestures(gestures)
    return uow


def _cited(when: float) -> dict[str, Gesture]:
    return {one: _gesture(one, when, target) for one, target in DEMONSTRATED.items()}


def _since(run: WorkflowRun) -> float:
    from datetime import datetime

    assert run.finished_at
    return datetime.fromisoformat(run.finished_at).timestamp()


async def test_the_repair_is_written_against_the_job_step_the_row_was_of() -> None:
    """A job whose middle repeats is further along in the RUN than it is in the
    job -- `order` says where in the run, `of_step` which step of the job -- and
    a locator written under the run's own numbering belongs to another step or
    to no step at all."""
    run = _run(_held(0, 0), _held(1, 1), _failed(2, 0))
    since = _since(run)
    uow = await _uow(run, _gesture(BY_HAND.id, since + 4.0, BY_HAND.action.target or Target()))

    learned = await learn_from_the_rescue(uow, TENANT, JOB, _cited(since - 100.0))

    assert learned is not None
    assert (learned.ord, learned.strategy, learned.query) == (0, "role_and_name", "button|Filter")


async def test_a_run_that_held_every_step_teaches_nothing() -> None:
    """Otherwise every successful run would mine whatever the operator did next
    into its first step -- which is not a repair, it is the next job."""
    run = _run(_held(0, 0), _held(1, 1))
    since = _since(run)
    uow = await _uow(run, _gesture(BY_HAND.id, since + 4.0, BY_HAND.action.target or Target()))

    assert await learn_from_the_rescue(uow, TENANT, JOB, _cited(since - 100.0)) is None


async def test_a_step_that_was_found_and_pressed_did_not_fail_for_a_locator() -> None:
    """The deployment's own shape, 2026-09-19. `Delete a Customer Type` failed
    five times running with `matched_by = component`: the browser found the
    filter dropdown by the job's own identity and pressed it, and the screen
    belt judged from a digest of the top nav bar that nothing had opened.

    The operator then carried on by hand -- and on one of those five the first
    thing they touched was the grid two steps further on. Learning that as the
    first thing to try for step 1 would point a delete job's opening click at a
    row in a table.
    """
    run = _run(_failed(0, 0))
    run.steps[0].matched_by = "component"
    since = _since(run)
    uow = await _uow(
        run,
        _gesture(
            "g-carried-on",
            since + 45.0,
            Target(role="presentation", css_path="td#ext-gen2782 > div.x-grid-cell-inner"),
        ),
    )

    assert await learn_from_the_rescue(uow, TENANT, JOB, _cited(since - 100.0)) is None


async def test_nothing_outside_the_window_reaches_the_job() -> None:
    """Through the repository and the rule together. The bound is asked for of
    the store -- a tenant with a year of gestures must not have a year of them
    loaded to find out nobody repaired anything -- and the rule applies it
    again, so this holds whichever of the two is doing the work."""
    run = _run(_failed(0, 0))
    since = _since(run)
    uow = await _uow(
        run,
        _gesture("g-yesterday", since - 86_400.0, BY_HAND.action.target or Target()),
        _gesture("g-tomorrow", since + K_SOON + 1.0, BY_HAND.action.target or Target()),
    )

    assert await learn_from_the_rescue(uow, TENANT, JOB, _cited(since - 100.0)) is None
