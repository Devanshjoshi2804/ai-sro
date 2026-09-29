from __future__ import annotations

import json

import pytest

from sro.domain.execution.takeover import OPERATOR, Takeover, Took, take_over
from sro.domain.observation.gesture import Action, Body, Call, Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.workflow import Step, Workflow

SYSTEM = "https://wms.example"
APP = f"{SYSTEM}/app"
SAVE = f"{SYSTEM}/api/customer-types"
TOOK = Took(tab_id=7, since=90.0, through=100.0, newest=100.0)
VALUES = {"First": "GT1", "Second": "GT2"}


def posted(name: str, at: float, status: int | None = 201) -> Call:
    body = Body(text=json.dumps({"name": name}), mime_type="application/json")
    return Call("POST", SAVE, started_at=at, status=status, request_body=body)


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
    """Type, save, type, save: each save demonstrated twice, so which
    parameter each one writes is known (`wanted_by`)."""
    recorded = [
        gesture("g0", 1.0, "type"),
        gesture("g1", 2.0, "click", calls=(posted("A1", 2.0),)),
        gesture("g2", 3.0, "type"),
        gesture("g3", 4.0, "click", calls=(posted("B1", 4.0),)),
        gesture("h1", 12.0, "click", calls=(posted("A2", 12.0),)),
        gesture("h3", 14.0, "click", calls=(posted("B2", 14.0),)),
    ]
    cites = [["g0"], ["g1", "h1"], ["g2"], ["g3", "h3"]]
    steps = [Step(order=n, says=f"s{n}", system=SYSTEM, cites=cites[n]) for n in range(4)]
    workflow = Workflow(
        id="wfl",
        tenant="t",
        title="Two saves",
        narrative="n",
        steps=steps,
        parameters=[
            {"name": "First", "seen_values": ["A1", "A2"]},
            {"name": "Second", "seen_values": ["B1", "B2"]},
        ],
    )
    return workflow, {one.id: one for one in recorded}


def operator_saved(
    at: float, name: str = "GT1", *, status: int | None = 201, tab: int = 7
) -> Gesture:
    return gesture(
        f"op{at}", at, "click", stream="dev-1", tab=tab, calls=(posted(name, at, status),)
    )


def took_over(matched: int, seen: list[Gesture], took: Took = TOOK, **values: str) -> Takeover:
    workflow, by_id = job()
    return take_over(
        workflow, by_id, matched=matched, took=took, seen=seen, values={**VALUES, **values}
    )


def test_a_save_the_operator_s_own_call_confirms_is_done_and_the_run_begins_after_it() -> None:
    assert took_over(3, [operator_saved(100.0)]) == Takeover(replay_from=2, done=(1,))


def test_a_form_the_operator_only_filled_is_replayed_from_the_start() -> None:
    typed = gesture("t", 95.0, "type", stream="dev-1", tab=7)

    assert took_over(1, [typed], Took(7, 90.0, 95.0, 95.0)) == Takeover(replay_from=0)


def test_a_save_not_yet_uploaded_is_in_doubt_never_assumed() -> None:
    took = took_over(3, [operator_saved(100.0)], Took(7, 90.0, 105.0, 105.0))

    assert took == Takeover(replay_from=0, in_doubt=(1,))


def test_an_unanswered_or_broken_save_is_in_doubt() -> None:
    for status in (503, None):
        took = took_over(3, [operator_saved(100.0, status=status)])
        assert (took.done, took.in_doubt) == ((), (1,)), status


def test_a_refused_save_proves_it_was_not_written_and_it_is_made_again() -> None:
    for status in (400, 403, 404, 422):
        assert took_over(3, [operator_saved(100.0, status=status)]) == Takeover(0), status


def test_a_conflicting_save_may_be_this_one_and_is_in_doubt() -> None:
    took = took_over(3, [operator_saved(100.0, status=409)])

    assert took == Takeover(replay_from=0, in_doubt=(1,))


def test_another_tab_s_save_proves_nothing_and_is_never_ignored() -> None:
    assert took_over(3, [operator_saved(95.0, tab=8)]).in_doubt == (1,)


def test_a_save_made_before_this_doing_began_proves_nothing() -> None:
    assert took_over(3, [operator_saved(80.0)]).in_doubt == (1,)


def test_the_first_gesture_of_the_doing_counts() -> None:
    assert took_over(3, [operator_saved(100.0)], Took(7, 100.0, 100.0, 100.0)).done == (1,)


def test_a_save_past_a_stale_offer_is_in_doubt_never_sent_again() -> None:
    typed = gesture("t", 95.0, "type", stream="dev-1", tab=7)

    for tab in (7, 8):
        took = took_over(1, [typed, operator_saved(100.0, tab=tab)], Took(7, 90.0, 95.0, 100.0))
        assert took == Takeover(replay_from=0, in_doubt=(1,)), tab


def test_only_a_step_s_own_call_confirms_it() -> None:
    seen = [operator_saved(96.0, "GT1", status=422), operator_saved(100.0, "GT2")]

    assert took_over(4, seen) == Takeover(replay_from=0, done=(3,))


def test_one_save_leaves_the_next_one_it_reached_in_doubt() -> None:
    took = took_over(4, [operator_saved(100.0)])

    assert took == Takeover(replay_from=2, done=(1,), in_doubt=(3,))


def test_a_call_two_steps_could_own_proves_neither() -> None:
    took = took_over(4, [operator_saved(100.0, "GT")], First="GT", Second="GT")

    assert took == Takeover(replay_from=0, in_doubt=(1, 3))


def test_a_job_the_operator_finished_leaves_nothing_to_replay() -> None:
    seen = [operator_saved(95.0), operator_saved(100.0, "GT2")]

    assert took_over(4, seen) == Takeover(replay_from=4, done=(1, 3))


def test_a_takeover_cannot_end_before_it_begins() -> None:
    with pytest.raises(InvariantViolation):
        Took(tab_id=7, since=100.0, through=90.0, newest=100.0)
    with pytest.raises(InvariantViolation):
        Took(tab_id=7, since=90.0, through=100.0, newest=95.0)


def test_a_takeover_s_progress_never_sends_the_operator_s_write_again() -> None:
    progress = Takeover(replay_from=2, done=(1,), in_doubt=(3,)).progress()

    assert progress.step == 2
    assert progress.written(1) and progress.marks[1].lane == OPERATOR
    assert progress.in_doubt(3)
    progress.settle(1, lane="ui", verdict="failed")
    assert progress.written(1)


def test_a_refusal_does_not_hide_another_save_that_may_be_this_one() -> None:
    seen = [operator_saved(96.0, "GT1", status=422), operator_saved(99.0, "GT9", tab=8)]

    assert took_over(3, seen) == Takeover(replay_from=0, in_doubt=(1, 3))
