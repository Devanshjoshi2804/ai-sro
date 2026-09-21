"""A step naming the earlier steps whose output it consumes.

CrewAI's `Task.context`, and its argument: a task that names the prior tasks it
depends on can be READ. One inspectable line answers "how does step five get
step two's id", where an implicit shared map means reading the whole job and
guessing.

Empty on every job mined so far, and honestly so -- thirteen runs on this
deployment have made a record and not one has made two. What these pin is the
rules the edge is held to, so that the day something emits one, a job that
could not run is refused at the door rather than in front of a warehouse form.
"""

from __future__ import annotations

from sro.application.execution.run_workflow import _what_earlier_steps_made
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.skill.checks import validate
from sro.domain.skill.workflow import Step, Workflow

EVIDENCE = {"ges-0": "https://wms.example", "ges-1": "https://wms.example"}


def _job(*uses: list[int]) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="create a customer type and file it",
        narrative="two records, and the second names the first",
        systems=["https://wms.example"],
        steps=[
            Step(
                order=n,
                says=f"step {n}",
                system="https://wms.example",
                cites=[f"ges-{n}"],
                uses=list(one),
            )
            for n, one in enumerate(uses)
        ],
    )


def _run(*made: tuple[int, dict[str, str]]) -> WorkflowRun:
    run = WorkflowRun(
        id="run_1",
        tenant="acme",
        workflow_id="wfl_1",
        device_id="dev-1",
        started_by="devansh",
        values={},
        live=True,
        allow_focus=False,
        started_at="2026-09-19T00:00:00Z",
    )
    run.steps = [
        RunStep(order=n, of_step=order, says="s", verdict="held", made=dict(fields))
        for n, (order, fields) in enumerate(made)
    ]
    return run


def test_a_step_that_uses_a_later_step_is_refused() -> None:
    """Forwards is a job that cannot run: the value is not made until later, so
    a run reaching step zero for step one's record would bind nothing and type
    an empty box."""
    refused = validate(_job([1], []), EVIDENCE)

    assert refused is not None
    assert refused.reason == "step uses a later step"


def test_a_step_that_uses_itself_is_the_same_fault_written_smaller() -> None:
    refused = validate(_job([], [1]), EVIDENCE)

    assert refused is not None and refused.reason == "step uses a later step"


def test_a_step_that_uses_a_step_that_is_not_there_is_refused() -> None:
    """A model inventing an edge, which is the one thing citation exists to
    refuse everywhere else here.

    Orders with a GAP in them, because that is the only shape this can happen
    in and it is a shape that occurs: `workflow_from` drops junk steps one at a
    time, so a kept job can be steps 0 and 5 with nothing between."""
    job = Workflow(
        id="wfl_1",
        tenant="acme",
        title="a job with a hole in it",
        narrative="n",
        systems=["https://wms.example"],
        steps=[
            Step(order=0, says="s", system="https://wms.example", cites=["ges-0"]),
            Step(order=5, says="s", system="https://wms.example", cites=["ges-1"], uses=[3]),
        ],
    )

    refused = validate(job, EVIDENCE)

    assert refused is not None
    assert refused.reason == "step uses a step that is not there"


def test_a_step_that_uses_an_earlier_step_is_kept() -> None:
    assert validate(_job([], [0]), EVIDENCE) is None


def test_a_job_where_nothing_uses_anything_is_what_every_job_is_today() -> None:
    assert validate(_job([], []), EVIDENCE) is None


def test_what_an_earlier_step_made_arrives_under_its_own_name() -> None:
    """`step<order>.<field>`, never merged flat: a create answering `{"id":
    ...}` and a job with a parameter called `id` would otherwise silently be
    the same value."""
    made = _what_earlier_steps_made(_run((2, {"id": "1234", "code": "DDLS"})), [2])

    assert made == {"step2.id": "1234", "step2.code": "DDLS"}


def test_a_step_that_made_nothing_contributes_nothing() -> None:
    assert _what_earlier_steps_made(_run((2, {})), [2]) == {}


def test_a_step_that_has_not_run_yet_contributes_nothing() -> None:
    """Which the checks refuse, and this must not depend on them having."""
    assert _what_earlier_steps_made(_run((2, {"id": "1"})), [5]) == {}


def test_the_last_attempt_of_a_repeating_step_is_the_one_that_counts() -> None:
    """A repeating job performs one step.order once per item. The record this
    item is about is the one that step just made, not the one it made for the
    item before."""
    made = _what_earlier_steps_made(_run((2, {"id": "first"}), (2, {"id": "second"})), [2])

    assert made == {"step2.id": "second"}
