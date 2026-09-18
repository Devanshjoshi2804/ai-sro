"""The producer for `Step.uses`: an edge read off the evidence.

The rule is narrow on purpose. It is not "step five typed something step two
also had" -- a job that types one code into two screens would read as a
dependency, and it is one parameter typed twice. It is "step five used
something that did not exist until step two was answered": a value in step
two's response that was not in step two's request. An id the warehouse minted,
which the later step could not have known any other way.
"""

from __future__ import annotations

import json

from sro.domain.execution.uses_edges import uses_edges
from sro.domain.observation.gesture import Action, Body, Call, Gesture
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.example"


def _call(sent: dict[str, object], back: dict[str, object] | None) -> Call:
    said = json.dumps(sent)
    return Call(
        method="POST",
        url=f"{WMS}/records",
        status=201,
        request_body=Body(text=said, size_bytes=len(said)),
        response_body=None if back is None else Body(text=json.dumps({"data": back}), size_bytes=1),
    )


def _doing(
    gesture_id: str, *, typed: str | None = None, calls: list[Call] | None = None
) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=1.0,
        url=f"{WMS}/screen",
        system=WMS,
        tab_id=1,
        frame_url=None,
        action=Action(kind="type" if typed else "click", at=1.0, value=typed, url=f"{WMS}/screen"),
        requests=tuple(calls or []),
    )


def _job(steps: list[Step]) -> Workflow:
    return Workflow(id="wfl_1", tenant="acme", title="t", narrative="n", steps=steps)


def _step(order: int, *cites: str) -> Step:
    return Step(order=order, says=f"step {order}", system=WMS, cites=list(cites))


def test_a_value_the_warehouse_minted_and_a_later_step_used_is_an_edge() -> None:
    """Two doings, two different ids, each tracked. That is what makes it an
    edge rather than a coincidence."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"code": "GGD", "id": "REC-111"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"code": "GKB", "id": "REC-222"})]),
        "b1": _doing("b1", typed="REC-111"),
        "b2": _doing("b2", typed="REC-222"),
    }

    edges = uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made)

    assert edges == {2: [1]}


def test_one_parameter_typed_into_two_screens_is_not_a_dependency() -> None:
    """The case the rule is narrow for. `GGD` went INTO step one, so step two
    typing it is the operator's own value again -- not something step one
    produced."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"code": "GGD", "id": "REC-111"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"code": "GKB", "id": "REC-222"})]),
        "b1": _doing("b1", typed="GGD"),
        "b2": _doing("b2", typed="GKB"),
    }

    edges = uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made)

    assert edges == {}


def test_a_doing_that_did_not_track_it_refuses_the_edge() -> None:
    """`all`. One doing that used the id proves nothing if the other did not --
    which is what tells a real dependency from a value that happened to match
    once."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"code": "GGD", "id": "REC-111"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"code": "GKB", "id": "REC-222"})]),
        "b1": _doing("b1", typed="REC-111"),
        "b2": _doing("b2", typed="something else"),
    }

    edges = uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made)

    assert edges == {}


def test_a_step_that_answered_nothing_produces_nothing() -> None:
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, None)]),
        "b1": _doing("b1", typed="GGD"),
    }

    assert uses_edges(_job([_step(1, "a1"), _step(2, "b1")]), made) == {}


def test_an_edge_is_only_ever_backwards() -> None:
    """Step one cannot use step two's answer: it had not been given one."""
    made = {
        "a1": _doing("a1", typed="REC-111"),
        "b1": _doing("b1", calls=[_call({"code": "GGD"}, {"id": "REC-111"})]),
    }

    edges = uses_edges(_job([_step(1, "a1"), _step(2, "b1")]), made)

    assert 1 not in edges


def test_a_short_value_is_a_coincidence_and_not_an_edge() -> None:
    """`0`, `-1` and `SG` are all over a warehouse form."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"code": "GGD", "site": "SG"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"code": "GKB", "site": "SG"})]),
        # Posted rather than typed, so the value goes through the body reader
        # and not the typed-value filter: both drop it, and this is the one
        # that would otherwise be untested.
        "b1": _doing("b1", calls=[_call({"site": "SG"}, None)]),
        "b2": _doing("b2", calls=[_call({"site": "SG"}, None)]),
    }

    assert uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made) == {}


def test_a_short_value_somebody_typed_is_not_an_edge_either() -> None:
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"code": "GGD", "site": "SG"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"code": "GKB", "site": "SG"})]),
        "b1": _doing("b1", typed="SG"),
        "b2": _doing("b2", typed="SG"),
    }

    assert uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made) == {}


def test_two_steps_never_recorded_together_are_not_an_edge() -> None:
    """`all(())` is True, and an edge out of two steps with no doing in common
    is an edge out of nothing."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"id": "REC-111"})]),
        "b1": _doing("b1"),
    }

    assert uses_edges(_job([_step(1, "a1"), _step(2, "b1")]), made) == {}


def test_a_value_a_later_step_posted_counts_as_using_it() -> None:
    """A step reaches a value two ways and the evidence records them
    differently: an operator pasting an id into a box, and a page posting one
    it held."""
    made = {
        "a1": _doing("a1", calls=[_call({"code": "GGD"}, {"id": "REC-111"})]),
        "a2": _doing("a2", calls=[_call({"code": "GKB"}, {"id": "REC-222"})]),
        "b1": _doing("b1", calls=[_call({"parent": "REC-111"}, None)]),
        "b2": _doing("b2", calls=[_call({"parent": "REC-222"}, None)]),
    }

    assert uses_edges(_job([_step(1, "a1", "a2"), _step(2, "b1", "b2")]), made) == {2: [1]}
