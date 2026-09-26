"""A run keeps the version of its job it started with (X11).

Growing a job -- mining's `_grow` or `learn_field` -- renumbers its steps. A
run already going holds `progress.step`, an index, and marks keyed by step
order: read against the renumbered job it would skip a step, or send a write
it already sent. So a run reads only the steps it was started with, and what
the job learns by step number is taught and read only while the run's steps
are still the job's."""

import asyncio
from dataclasses import replace

from sro.application.runtime.teach import Teach
from sro.domain.execution.compose import Composed
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.progress import Progress
from sro.domain.execution.takeover import Takeover
from sro.domain.observation.gesture import Gesture, Outline, OutlineField
from sro.domain.skill.workflow import Step
from tests.unit.fakes import FakeClock
from tests.unit.runtime_support import (
    CTX,
    NOW,
    TENANT,
    WORKFLOW,
    SteelRun,
    save_step,
    steel_run,
    type_step,
)

DEPARTMENT = OutlineField("combobox", "Department", None, ("Finance", "Operations"))
FRAME = '[{"index": 1, "url": "https://wms.example/frames/form"}]'


async def _two_saves_one_done(*later: StepResult) -> SteelRun:
    """Type, save, type, save -- run through its first save; the UI lane
    answers `later` after that, or `done` twice."""
    world = await steel_run(
        steps=[
            type_step(gid="ges_t0", at=1.0),
            save_step(gid="ges_s1", at=2.0),
            type_step(gid="ges_t2", at=3.0),
            save_step(gid="ges_s3", at=4.0),
        ]
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))
    world.lanes.ui.answers(*(later or (StepResult("done", Lane.UI), StepResult("done", Lane.UI))))
    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    return world


async def _rest(world: SteelRun) -> str:
    """Runs the rest in a fresh worker, as a retry after a crash would."""
    steps = world.restarted()
    while (await steps.step(CTX, world.run_id, stop=asyncio.Event())).more:
        pass
    return await steps.finish(CTX, world.run_id)


async def _done(world: SteelRun) -> list[tuple[int, str]]:
    return [(one.of_step, one.says) for one in (await world.saved_run()).steps]


PINNED = [
    (0, "Type the customer type"),
    (1, "Save the customer type"),
    (2, "Type the customer type"),
    (3, "Save the customer type"),
]


async def test_a_mining_grow_mid_run_leaves_the_run_on_its_steps_and_sends_nothing_twice() -> None:
    world = await _two_saves_one_done()
    job = await world.job()
    grown = replace(
        job,
        steps=[
            Step(order=0, says="Open the menu", system=None, cites=["ges_menu"]),
            *(replace(one, order=one.order + 1) for one in job.steps),
        ],
    )
    await world.uow.workflows.grew(grown, moved={one.order: one.order + 1 for one in job.steps})

    assert await _rest(world) == "held"
    assert world.lanes.ui.calls == 4
    assert await _done(world) == PINNED


async def test_a_learned_field_mid_run_leaves_the_run_on_its_steps_and_sends_nothing_twice() -> (
    None
):
    world = await _two_saves_one_done()
    other_runs_job = await world.job()

    await Teach(world.uow, FakeClock()).learn_field(
        CTX,
        other_runs_job,
        Composed("department", "Department", "combobox", 1),
        key="department",
        value="Finance",
        learned={},
        lane=Lane.UI,
        run_id="run_other",
    )

    assert len((await world.job()).steps) == 5
    assert await _rest(world) == "held"
    assert world.lanes.ui.calls == 4
    assert await _done(world) == PINNED


async def test_a_run_that_is_behind_the_job_neither_reads_nor_teaches_by_step_number() -> None:
    """The job's locators and broken lanes are keyed by its own numbering; a
    run on an older numbering would read another step's locator, or teach
    one under another step's number."""
    sighted = {"strategy": "css", "query": "#typed", "frame_path": FRAME}
    world = await _two_saves_one_done(StepResult("done", Lane.SIGHT, learned=sighted))
    job = await world.job()
    await world.uow.workflows.remember_locator(job.id, LearnedStep(2, "css", "#other", "sight"))
    grown = replace(
        job,
        steps=[
            Step(order=0, says="Open the menu", system=None, cites=["ges_menu"]),
            *(replace(one, order=one.order + 1) for one in job.steps),
        ],
    )
    await world.uow.workflows.grew(grown, moved={one.order: one.order + 1 for one in job.steps})

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.contexts[-1].learned == {}
    assert [(one.ord, one.query) for one in await world.learned()] == [(3, "#other")]


async def test_two_runs_on_one_version_grow_the_job_once_and_the_later_learns_nothing() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    job = await world.job()
    teach = Teach(world.uow, FakeClock())

    await teach.learn_field(
        CTX,
        job,
        Composed("department", "Department", "combobox", 0),
        key="department",
        value="Finance",
        learned={},
        lane=Lane.UI,
        run_id="run_1",
    )
    await teach.learn_field(
        CTX,
        job,
        Composed("region", "Region", "combobox", 0),
        key="region",
        value="North",
        learned={},
        lane=Lane.UI,
        run_id="run_2",
    )

    assert [(one.order, one.says) for one in (await world.job()).steps] == [
        (0, "Fill Department"),
        (1, "Save the customer type"),
    ]


async def test_a_stuck_running_run_no_longer_blocks_learning() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.another_run("run_stuck")
    job = await world.job()

    await Teach(world.uow, FakeClock()).learn_field(
        CTX,
        job,
        Composed("department", "Department", "combobox", 0),
        key="department",
        value="Finance",
        learned={},
        lane=Lane.UI,
        run_id=world.run_id,
    )

    assert [one.says for one in (await world.job()).steps] == [
        "Fill Department",
        "Save the customer type",
    ]


async def test_a_takeover_whose_mail_values_a_field_the_operator_saved_still_holds() -> None:
    """The operator saved the first form themselves; a value for a field on
    that form is theirs to have decided, and never blocks `held`."""
    progress = Takeover(2, done=(1,)).progress()
    world = await steel_run(
        steps=[
            type_step(gid="ges_t0", at=1.0),
            save_step(gid="ges_s1", at=2.0, outline=Outline(fields=(DEPARTMENT,))),
            type_step(gid="ges_t2", at=3.0),
            save_step(gid="ges_s3", at=4.0, outline=Outline()),
        ],
        progress=progress,
        values={"Customer Type": "GT1", "department": "Finance"},
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    assert world.progress().composed == []
    assert await _rest(world) == "held"
    assert world.lanes.ui.calls == 2


REGION = OutlineField("combobox", "Region", None, ("North", "South"))


def _four_steps(*, on_first: Outline, on_second: Outline) -> list[tuple[Step, dict[str, Gesture]]]:
    return [
        type_step(gid="ges_t0", at=1.0),
        save_step(gid="ges_s1", at=2.0, outline=on_first),
        type_step(gid="ges_t2", at=3.0),
        save_step(gid="ges_s3", at=4.0, outline=on_second),
    ]


async def test_a_field_on_a_save_the_operator_made_after_the_resume_point_never_blocks_held() -> (
    None
):
    """`take_over` resumes at the first write not done, so a later write can
    be the operator's already: here they saved the second form, not the first."""
    world = await steel_run(
        steps=_four_steps(on_first=Outline(), on_second=Outline(fields=(DEPARTMENT,))),
        progress=Takeover(0, done=(3,)).progress(),
        values={"Customer Type": "GT1", "department": "Finance"},
    )
    world.lanes.ui.answers(*(StepResult("done", Lane.UI) for _ in range(3)))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    assert world.progress().composed == []
    assert await _rest(world) == "held"
    assert world.lanes.ui.calls == 3


def _confirmed(name: str, label: str, before: int) -> dict[str, object]:
    return {
        "name": name,
        "label": label,
        "role": "combobox",
        "before": before,
        "options": None,
        "lane": "ui",
        "verdict": "done",
        "key": name,
        "learned": {},
    }


async def test_a_retried_finish_learns_the_fields_the_first_attempt_did_not_reach() -> None:
    progress = Progress(step=4)
    progress.composed = [
        _confirmed("department", "Department", 1),
        _confirmed("region", "Region", 3),
    ]
    world = await steel_run(
        steps=_four_steps(
            on_first=Outline(fields=(DEPARTMENT,)), on_second=Outline(fields=(REGION,))
        ),
        progress=progress,
        values={"Customer Type": "GT1", "department": "Finance", "region": "North"},
    )
    pinned = await world.job()
    await Teach(world.uow, FakeClock()).learn_field(
        CTX,
        pinned,
        Composed("region", "Region", "combobox", 3),
        key="region",
        value="North",
        learned={},
        lane=Lane.UI,
        run_id=world.run_id,
    )

    await world.restarted().finish(CTX, world.run_id)

    assert [one.says for one in (await world.job()).steps] == [
        "Type the customer type",
        "Fill Department",
        "Save the customer type",
        "Type the customer type",
        "Fill Region",
        "Save the customer type",
    ]


async def test_a_job_retired_mid_run_is_finished_on_the_run_s_own_steps() -> None:
    sighted = {"strategy": "css", "query": "#typed", "frame_path": FRAME}
    world = await _two_saves_one_done(
        StepResult("done", Lane.SIGHT, learned=sighted), StepResult("done", Lane.UI)
    )
    await world.uow.workflows.retire(TENANT, WORKFLOW.id, at=NOW)

    assert await _rest(world) == "held"
    assert world.lanes.ui.calls == 4
    assert await _done(world) == PINNED
    assert await world.uow.workflows.learned_for(WORKFLOW.id) == ()
