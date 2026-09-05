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


def test_origin_prefers_the_call_and_falls_back_to_the_page() -> None:
    gestures = _gestures()
    with_calls = next(g for g in gestures if g.requests)
    without = next(g for g in gestures if not g.requests)
    with_calls.requests[0].url = "https://wms.example/data/x"
    assert origin_of(with_calls) == "https://wms.example"
    assert origin_of(without) == "http://127.0.0.1:63319"


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

    # 127.0.0.1:1 is the fixture's deliberately failed fetch: a call that never
    # landed still names an origin this session reached for, and the allowlist
    # is what the evidence names, not what it got an answer from.
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
