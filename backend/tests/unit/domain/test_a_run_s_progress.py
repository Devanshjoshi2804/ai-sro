from sro.domain.execution.progress import K_BUDGET_FLOOR_S, Progress, run_budget
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.workflow import Step, Workflow


def timed_job(*, seconds: float, steps: int) -> tuple[Workflow, dict[str, Gesture]]:
    gestures = {
        f"g{n}": Gesture(
            id=f"g{n}",
            tenant="t",
            stream_id="s",
            batch_id="b",
            at=n * seconds / max(steps - 1, 1),
            url=None,
            system=None,
            tab_id=1,
            frame_url=None,
            action=Action(kind="click", at=0.0),
        )
        for n in range(steps)
    }
    job = Workflow(
        id="wfl_t",
        tenant="t",
        title="t",
        narrative="n",
        steps=[Step(order=n, says=f"s{n}", system=None, cites=[f"g{n}"]) for n in range(steps)],
    )
    return job, gestures


def test_progress_survives_its_row() -> None:
    progress = Progress(step=2, read={"id": "ct-9"}, tabs={"main": "T1"}, lease="lse_1")
    progress.sending(1)
    progress.settle(0, lane="ui", verdict="done")

    again = Progress.of(progress.as_json())

    assert again == progress


def test_a_write_in_flight_is_in_doubt_and_never_written() -> None:
    progress = Progress()
    progress.sending(3)

    assert progress.in_doubt(3) and not progress.written(3)


def test_a_settled_write_is_written_once() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="api", verdict="done")

    assert progress.written(3) and not progress.in_doubt(3)


def test_the_budget_grows_with_what_the_operator_took() -> None:
    slow, quick = timed_job(seconds=600, steps=5), timed_job(seconds=20, steps=5)

    assert run_budget(*slow) > run_budget(*quick) >= K_BUDGET_FLOOR_S
