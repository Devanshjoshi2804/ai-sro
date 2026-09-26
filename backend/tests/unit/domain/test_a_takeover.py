from __future__ import annotations

import pytest

from sro.domain.execution.takeover import OPERATOR, Takeover, Took, take_over
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.workflow import Step, Workflow

SYSTEM = "https://wms.example"
APP = f"{SYSTEM}/app"
SAVE = f"{SYSTEM}/api/customer-types"
TOOK = Took(tab_id=7, since=90.0, through=100.0)


def gesture(
    gid: str,
    at: float,
    kind: str,
    *,
    calls: tuple[Call, ...] = (),
    stream: str = "rec",
    tab: int = 1,
) -> Gesture:
    return Gesture(
        id=gid,
        tenant="t",
        stream_id=stream,
        batch_id="b",
        at=at,
        url=APP,
        system=SYSTEM,
        tab_id=tab,
        frame_url=None,
        action=Action(kind=kind, at=at),
        requests=list(calls),
    )


def job() -> tuple[Workflow, dict[str, Gesture]]:
    recorded = [
        gesture("g0", 1.0, "type"),
        gesture("g1", 2.0, "click", calls=(Call("POST", SAVE, started_at=2.0, status=201),)),
        gesture("g2", 3.0, "type"),
        gesture("g3", 4.0, "click", calls=(Call("POST", SAVE, started_at=4.0, status=201),)),
    ]
    steps = [Step(order=n, says=f"s{n}", system=SYSTEM, cites=[f"g{n}"]) for n in range(4)]
    workflow = Workflow(id="wfl", tenant="t", title="Two saves", narrative="n", steps=steps)
    return workflow, {one.id: one for one in recorded}


def operator_saved(at: float, *, status: int | None = 201, tab: int = 7) -> Gesture:
    return gesture(
        f"op{at}",
        at,
        "click",
        stream="dev-1",
        tab=tab,
        calls=(Call("POST", SAVE, started_at=at, status=status),),
    )


def test_a_save_the_operator_s_own_call_confirms_is_done_and_the_run_begins_after_it() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0)])

    assert took == Takeover(replay_from=2, done=(1,), in_doubt=())


def test_a_form_the_operator_only_filled_is_replayed_from_the_start() -> None:
    workflow, by_id = job()
    typed = gesture("t", 95.0, "type", stream="dev-1", tab=7)

    took = take_over(workflow, by_id, matched=1, took=Took(7, 90.0, 95.0), seen=[typed])

    assert took == Takeover(replay_from=0)


def test_a_save_not_yet_uploaded_is_in_doubt_never_assumed() -> None:
    workflow, by_id = job()

    took = take_over(
        workflow, by_id, matched=3, took=Took(7, 90.0, 105.0), seen=[operator_saved(100.0)]
    )

    assert took == Takeover(replay_from=0, in_doubt=(1,))


def test_a_refused_or_unanswered_save_is_in_doubt() -> None:
    workflow, by_id = job()

    for status in (409, 503, None):
        took = take_over(
            workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0, status=status)]
        )
        assert (took.done, took.in_doubt) == ((), (1,)), status


def test_another_tab_s_save_proves_nothing() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0, tab=8)])

    assert took.in_doubt == (1,)


def test_a_save_made_before_this_doing_began_proves_nothing() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(80.0)])

    assert took.in_doubt == (1,)


def test_the_first_gesture_of_the_doing_counts() -> None:
    workflow, by_id = job()

    took = take_over(
        workflow, by_id, matched=3, took=Took(7, 100.0, 100.0), seen=[operator_saved(100.0)]
    )

    assert took.done == (1,)


def test_a_takeover_cannot_end_before_it_begins() -> None:
    with pytest.raises(InvariantViolation):
        Took(tab_id=7, since=100.0, through=90.0)


def test_a_takeover_s_progress_never_sends_the_operator_s_write_again() -> None:
    progress = Takeover(replay_from=2, done=(1,), in_doubt=(3,)).progress()

    assert progress.step == 2
    assert progress.written(1) and progress.marks[1].lane == OPERATOR
    assert progress.in_doubt(3)
    progress.settle(1, lane="ui", verdict="failed")
    assert progress.written(1)


def test_one_call_of_the_operator_s_confirms_one_write_never_two_alike() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=4, took=TOOK, seen=[operator_saved(100.0)])

    assert took == Takeover(replay_from=2, done=(1,), in_doubt=(3,))


def test_a_job_the_operator_finished_leaves_nothing_to_replay() -> None:
    workflow, by_id = job()
    seen = [operator_saved(95.0), operator_saved(100.0)]

    took = take_over(workflow, by_id, matched=4, took=TOOK, seen=seen)

    assert took == Takeover(replay_from=4, done=(1, 3))
