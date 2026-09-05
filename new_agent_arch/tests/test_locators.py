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
from rig.wire import Batch
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
