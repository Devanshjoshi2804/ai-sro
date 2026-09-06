import copy

from rig.correlate import correlate
from rig.locators import (
    allowlist,
    locators_for,
    origin_of,
    primary_gesture,
    recorded_call,
    writes,
)
from rig.wire import Batch, Request
from rig.workflows import Step, Workflow
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def test_the_ladder_is_the_protocols_and_in_its_order() -> None:
    save = next(
        g
        for g in _gestures()
        if g.gesture.target
        and g.gesture.target.component
        and g.gesture.target.component.itemId == "saveButton"
    )
    t = save.gesture.target
    t.role, t.name, t.text, t.testId, t.cssPath = (
        "button",
        "Save",
        "Save",
        "save-btn",
        "div > button",
    )
    t.component.query = "button#saveButton"

    ladder = locators_for(save)

    assert [rung["strategy"] for rung in ladder] == [
        "component",
        "role_and_name",
        "text",
        "test_id",
        "css_path",
    ]
    assert ladder[0]["query"] == "button#saveButton"
    assert ladder[1]["query"] == "button|Save"
    assert all(rung["within"] is None and rung["visible_only"] is True for rung in ladder)


def test_an_item_id_alone_is_still_a_component_query() -> None:
    g = copy.deepcopy(_gestures()[0])
    g.gesture.target.component.query = None
    assert locators_for(g)[0] == {
        "strategy": "component",
        "query": "#clientCode",
        "within": None,
        "visible_only": True,
    }


def test_a_scroll_has_no_ladder_and_a_step_citing_only_scrolls_has_no_primary() -> None:
    g = copy.deepcopy(_gestures()[0])
    g.gesture.kind, g.gesture.target = "scroll", None
    assert locators_for(g) == []
    assert (
        primary_gesture(Step(order=0, says="scroll", system=None, cites=[g.id]), {g.id: g}) is None
    )


def test_origin_is_the_page_and_a_call_only_when_the_page_has_none() -> None:
    gestures = _gestures()
    with_calls = next(g for g in gestures if g.requests)
    without = next(g for g in gestures if not g.requests)
    with_calls.requests[0].url = "https://wms.example/data/x"

    # The page wins even though a call names somewhere else entirely.
    assert origin_of(with_calls) == "http://127.0.0.1:63319"
    assert origin_of(without) == "http://127.0.0.1:63319"

    with_calls.url, with_calls.system = None, None
    assert origin_of(with_calls) == "https://wms.example"


def test_origin_skips_a_call_that_never_completed() -> None:
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.url, gesture.system = None, None
    dead, live = gesture.requests[0], gesture.requests[1]
    dead.url, dead.status, dead.failure_reason = "http://127.0.0.1:1/x", None, "Failed to fetch"
    live.url, live.status, live.failure_reason = "https://wms.example/y", 200, None
    gesture.requests = [dead, live]

    assert origin_of(gesture) == "https://wms.example"


def test_the_allowlist_is_every_system_the_evidence_names_and_nothing_else() -> None:
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    saver.requests[0].url = "https://wms.example/data/x"
    wf = Workflow(
        id="wfl_1",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=[g.id for g in gestures])],
    )

    # 127.0.0.1:1 is the fixture's deliberately failed fetch. The allowlist is
    # unfiltered on purpose: a call that never landed still names an origin this
    # session reached for, and the allowlist is what the evidence names rather
    # than what it got an answer from. `origin_of` makes the opposite call for
    # the opposite reason -- it steers a browser, so it takes the page first and
    # a failed call last, and never points a run at a host that is already dead.
    assert allowlist(wf, by_id) == {
        "http://127.0.0.1:63319",
        "http://127.0.0.1:1",
        "https://wms.example",
    }


def test_a_step_writes_when_any_cited_gesture_caused_a_mutation() -> None:
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    typer = next(g for g in gestures if not g.requests)
    assert writes(Step(order=0, says="save", system=None, cites=[saver.id]), by_id)
    assert not writes(Step(order=0, says="type", system=None, cites=[typer.id]), by_id)
    assert (
        recorded_call(Step(order=0, says="save", system=None, cites=[saver.id]), by_id).method
        == "POST"
    )


def _request(**over) -> Request:
    base = {
        "request_id": "r1",
        "method": "GET",
        "url": "https://wms.example/api/x",
        "started_at": "2026-08-31T08:40:04.765Z",
    }
    return Request.model_validate({**base, **over})


def test_a_cited_gesture_the_store_no_longer_holds_is_read_past_not_stopped_at() -> None:
    """A re-mine can drop a gesture a workflow still cites. The step's other
    evidence is still evidence."""
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    step = Step(order=0, says="save", system=None, cites=["ges_gone", saver.id])
    wf = Workflow(id="wfl_1", tenant="acme", title="t", narrative="n", steps=[step])

    call = recorded_call(step, by_id)
    assert call is not None and call.method == "POST"
    assert writes(step, by_id)
    assert allowlist(wf, by_id) == {"http://127.0.0.1:63319", "http://127.0.0.1:1"}


def test_a_step_that_only_read_names_its_first_read_and_does_not_write() -> None:
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [
        _request(request_id="a", url="https://wms.example/api/first", status=200),
        _request(request_id="b", url="https://wms.example/api/second", status=200),
    ]
    step = Step(order=0, says="open the list", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})

    assert call is not None and call.url.endswith("/first"), "the first read, not a later one"
    assert not writes(step, {gesture.id: gesture})


def test_a_preflight_or_a_probe_is_a_read_however_it_is_spelled() -> None:
    """HEAD and OPTIONS change nothing, so a step whose evidence carries only
    one of them is not a write a dry run must withhold."""
    for method in ("HEAD", "OPTIONS", "options"):
        gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
        gesture.requests = [_request(method=method, status=200)]
        step = Step(order=0, says="check", system=None, cites=[gesture.id])
        assert not writes(step, {gesture.id: gesture}), method
        assert recorded_call(step, {gesture.id: gesture}).method == method


def test_a_rung_needs_both_halves_of_what_it_matches_on_and_carries_its_own_query() -> None:
    g = copy.deepcopy(_gestures()[0])
    t = g.gesture.target
    t.component = None
    t.role, t.name = "textbox", None
    t.text, t.testId, t.cssPath = "Client code", "code-field", "form > input"

    ladder = locators_for(g)

    assert [rung["strategy"] for rung in ladder] == ["text", "test_id", "css_path"]
    assert [rung["query"] for rung in ladder] == ["Client code", "code-field", "form > input"]


def test_the_page_wins_over_a_call_and_a_gesture_with_no_page_falls_to_its_calls() -> None:
    g = copy.deepcopy(next(x for x in _gestures() if x.requests))
    g.system, g.url = "https://page.example", "http://frame.example/x"
    assert origin_of(g) == "https://page.example"

    g.system = None
    assert origin_of(g) == "http://frame.example", "the frame's url is still a page"


def test_a_call_that_names_no_system_is_not_the_origin_and_none_of_them_is_none() -> None:
    g = copy.deepcopy(next(x for x in _gestures() if x.requests))
    g.system, g.url = None, None
    g.requests = [
        _request(request_id="a", url="about:blank", status=200),
        _request(request_id="b", url="https://wms.example/api/x", status=200),
    ]
    assert origin_of(g) == "https://wms.example"

    g.requests = [_request(url="about:blank", status=None, failure_reason="Failed to fetch")]
    assert origin_of(g) is None
