import copy
from dataclasses import replace

from sro.domain.execution.evidence import (
    K_CAUSED_S,
    Locator,
    allowlist,
    locators_for,
    origin_of,
    primary_gesture,
    recorded_call,
    stood_on,
    writes,
)
from sro.domain.observation.gesture import Call
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures


def test_the_ladder_is_the_protocols_and_in_its_order() -> None:
    save = next(
        g
        for g in _gestures()
        if g.action.target
        and g.action.target.component
        and g.action.target.component.item_id == "saveButton"
    )
    t = save.action.target
    assert t is not None and t.component is not None
    new_target = replace(
        t,
        role="button",
        name="Save",
        text="Save",
        test_id="save-btn",
        css_path="div > button",
        component=replace(t.component, query="button#saveButton"),
    )
    save.action = replace(save.action, target=new_target)

    ladder = locators_for(save)

    assert [rung.strategy for rung in ladder] == [
        "component",
        "role_and_name",
        "text",
        "test_id",
        "css_path",
    ]
    assert ladder[0].query == "button#saveButton"
    assert ladder[1].query == "button|Save"
    assert [rung.as_payload() for rung in ladder] == [
        {
            "strategy": "component",
            "query": "button#saveButton",
            "within": None,
            "visible_only": True,
        },
        {"strategy": "role_and_name", "query": "button|Save", "within": None, "visible_only": True},
        {"strategy": "text", "query": "Save", "within": None, "visible_only": True},
        {"strategy": "test_id", "query": "save-btn", "within": None, "visible_only": True},
        {"strategy": "css_path", "query": "div > button", "within": None, "visible_only": True},
    ]


def test_an_item_id_alone_is_still_a_component_query() -> None:
    g = copy.deepcopy(_gestures()[0])
    t = g.action.target
    assert t is not None and t.component is not None
    component = replace(t.component, query=None)
    g.action = replace(g.action, target=replace(t, component=component))
    assert locators_for(g)[0] == Locator("component", "#clientCode")


def test_a_scroll_has_no_ladder_and_a_step_citing_only_scrolls_has_no_primary() -> None:
    g = copy.deepcopy(_gestures()[0])
    g.action = replace(g.action, kind="scroll", target=None)
    assert locators_for(g) == []
    assert (
        primary_gesture(Step(order=0, says="scroll", system=None, cites=[g.id]), {g.id: g}) is None
    )


def test_origin_is_the_page_and_a_call_only_when_the_page_has_none() -> None:
    gestures = _gestures()
    with_calls = next(g for g in gestures if g.requests)
    without = next(g for g in gestures if not g.requests)
    with_calls.requests[0] = replace(with_calls.requests[0], url="https://wms.example/data/x")

    # The page wins even though a call names somewhere else entirely.
    assert origin_of(with_calls) == "http://127.0.0.1:63319"
    assert origin_of(without) == "http://127.0.0.1:63319"

    with_calls.url, with_calls.system = None, None
    assert origin_of(with_calls) == "https://wms.example"


def test_origin_skips_a_call_that_never_completed() -> None:
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.url, gesture.system = None, None
    dead = replace(
        gesture.requests[0],
        url="http://127.0.0.1:1/x",
        status=None,
        failure_reason="Failed to fetch",
    )
    live = replace(gesture.requests[1], url="https://wms.example/y", status=200)
    gesture.requests = [dead, live]

    assert origin_of(gesture) == "https://wms.example"


def test_a_status_that_lies_about_completing_does_not_decide_the_origin() -> None:
    """A call can carry a 200 and still not have completed -- aborted after
    the browser already had a status line. `failure_reason` is what status
    alone cannot say."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.url, gesture.system = None, None
    aborted = replace(
        gesture.requests[0],
        url="http://127.0.0.1:1/x",
        status=200,
        failure_reason="net::ERR_ABORTED",
    )
    live = replace(gesture.requests[1], url="https://wms.example/y", status=200)
    gesture.requests = [aborted, live]

    assert origin_of(gesture) == "https://wms.example"


def test_the_allowlist_is_every_system_the_evidence_names_and_nothing_else() -> None:
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    saver.requests[0] = replace(saver.requests[0], url="https://wms.example/data/x")
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


def test_where_a_browser_may_be_sent_is_narrower_than_where_a_call_may_be_replayed() -> None:
    """Two sets, because they answer two questions about one job.

    `allowlist` carries the origin of every REQUEST a cited gesture produced,
    and it has to: `recorded_call` can name a call to an API origin the page
    itself never was, and `http.send` replays exactly that call.

    But a page calls whoever it likes. Measured on the deployment, 2026-09-15:
    `Create a Customer Type` cites a click in Gmail, a Gmail page calls
    Google's own infrastructure, and so `https://play.google.com` was an origin
    a planner could have NAVIGATED an operator's browser to -- on the evidence
    of a telemetry beacon, for a job about warehouse customer types. Nobody
    ever stood there.
    """
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    beacon = next(g for g in gestures if g.requests)
    beacon.requests[0] = replace(beacon.requests[0], url="https://play.google.com/log?id=1")
    wf = Workflow(
        id="wfl_1",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=[g.id for g in gestures])],
    )

    standing = stood_on(wf, by_id)
    replayable = allowlist(wf, by_id)

    assert "https://play.google.com" not in standing, "a beacon is not a place somebody was"
    assert "https://play.google.com" in replayable, "and a demonstrated call is still replayable"
    assert standing < replayable, "the narrow one is the wide one without the request origins"
    assert standing == {"http://127.0.0.1:63319"}


def test_a_step_writes_when_any_cited_gesture_caused_a_mutation() -> None:
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    typer = next(g for g in gestures if not g.requests)
    assert writes(Step(order=0, says="save", system=None, cites=[saver.id]), by_id)
    assert not writes(Step(order=0, says="type", system=None, cites=[typer.id]), by_id)
    call = recorded_call(Step(order=0, says="save", system=None, cites=[saver.id]), by_id)
    assert call is not None and call.method == "POST"


HOST = "http://127.0.0.1:63319"
"""The fixture gestures' own origin.

`recorded_call` reads only the calls on the gesture's OWN origin -- a page's
third-party traffic is not what the operator did -- so a planted call has to
be on the host the planted-on gesture happened on, or it is not that gesture's
evidence at all. These used to be planted on `wms.example` while every fixture
gesture is on `127.0.0.1:63319`, which made them cross-origin by accident."""


def _call(**over: object) -> Call:
    base: dict[str, object] = {"method": "GET", "url": f"{HOST}/api/x"}
    return Call(**{**base, **over})


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
        _call(url=f"{HOST}/api/first", status=200),
        _call(url=f"{HOST}/api/second", status=200),
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
        gesture.requests = [_call(method=method, status=200)]
        step = Step(order=0, says="check", system=None, cites=[gesture.id])
        assert not writes(step, {gesture.id: gesture}), method
        call = recorded_call(step, {gesture.id: gesture})
        assert call is not None and call.method == method


def test_a_rung_needs_both_halves_of_what_it_matches_on_and_carries_its_own_query() -> None:
    g = copy.deepcopy(_gestures()[0])
    assert g.action.target is not None
    t = replace(
        g.action.target,
        component=None,
        role="textbox",
        name=None,
        text="Client code",
        test_id="code-field",
        css_path="form > input",
    )
    g.action = replace(g.action, target=t)

    ladder = locators_for(g)

    assert [rung.strategy for rung in ladder] == ["text", "test_id", "css_path"]
    assert [rung.query for rung in ladder] == ["Client code", "code-field", "form > input"]


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
        _call(url="about:blank", status=200),
        _call(url="https://wms.example/api/x", status=200),
    ]
    assert origin_of(g) == "https://wms.example"

    g.requests = [_call(url="about:blank", status=None, failure_reason="Failed to fetch")]
    assert origin_of(g) is None


def test_a_telemetry_beacon_on_another_host_is_not_this_steps_write() -> None:
    """The bug that stopped every run this repository has ever recorded.

    Step 1 of tenant `new`'s `Create a Warehouse Equipment Type` is "Read the
    equipment type details from an email": a click on `mail.google.com` whose
    only recorded call is a `POST` to `play.google.com/log`, Google's telemetry
    beacon. `writes` read that as a mutation, so the run parked for a human
    approval on a beacon, and `verify` then demanded a read-back showing the
    value the run supplied -- which a beacon can never show. Six runs, six
    `stopped`, none past step 1.

    Measured over both real corpora: 144 of 360 mutating calls are
    cross-origin and every one of them is third-party. The real warehouse
    host's 79 are all same-origin, so this costs nothing where the work is.
    """
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [_call(method="POST", url="https://play.google.com/log", status=200)]
    step = Step(order=0, says="read the email", system=None, cites=[gesture.id])

    assert not writes(step, {gesture.id: gesture}), "a beacon is not the operator's write"
    assert recorded_call(step, {gesture.id: gesture}) is None, "and it is not this step's call"


def test_the_pages_own_write_is_still_the_steps_write() -> None:
    """The mirror, and the reason the one above is not just "ignore POSTs".

    The real WMS's every mutating call is on the page's own host, so the
    origin rule must leave a save exactly as it found it -- otherwise the
    change buys a run that never parks and never verifies anything.
    """
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [
        _call(method="POST", url="https://play.google.com/log", status=200),
        _call(method="POST", url=f"{HOST}/api/equipment-types", status=201),
    ]
    step = Step(order=0, says="click add", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})

    assert writes(step, {gesture.id: gesture}), "the page's own POST is the write"
    assert call is not None and call.url.endswith("/api/equipment-types")


def test_the_create_is_picked_over_the_beacon_beside_it() -> None:
    """Which call gets replayed stops resting on which one fired first.

    A gesture that saved a record also sent the page's telemetry batch, and
    both are POSTs on the warehouse's own host. Four steps across both real
    stores record exactly that pair; the create happened to come first in each,
    so the right call was replayed by luck. `CREATED` makes it a rule.
    """
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [
        _call(
            method="POST",
            url=f"{HOST}/data/WM/wm/webPerformanceEntries/batch",
            request_id="beacon",
            status=200,
        ),
        _call(method="POST", url=f"{HOST}/data/WM/wm/customerTypes", request_id="save", status=201),
    ]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})
    assert call is not None and call.url.endswith("/customerTypes")


def test_a_201_that_never_returned_is_not_the_call_to_prefer() -> None:
    """A status on a call reporting a failure is not a status the warehouse
    gave back -- the same reading `origin_of` and `expected_statuses` make. So
    the mutation that did come back is the one replayed."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [
        _call(method="POST", url=f"{HOST}/api/live", request_id="live", status=200),
        _call(
            method="POST",
            url=f"{HOST}/api/dead",
            request_id="dead",
            status=201,
            failure_reason="Failed to fetch",
        ),
    ]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})
    assert call is not None and call.url.endswith("/api/live")


def test_a_keep_alive_that_landed_seconds_later_is_not_this_gestures_call() -> None:
    """The page's own host is not enough: a session keep-alive and a telemetry
    batch are POSTs on the warehouse's own origin, and reading one as the
    step's write made a run withhold, park and then demand a read-back of a
    step that only types into a field. Four steps across both real stores were
    classified that way, three of them on the warehouse host.
    """
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    assert gesture.at is not None
    gesture.requests = [
        _call(
            method="POST",
            url=f"{HOST}/refs/data/api/v1/rp/admin/sessionKeepAlive",
            request_id="alive",
            started_at=gesture.at + 8.118,
            status=200,
        )
    ]
    step = Step(order=0, says="type a name", system=None, cites=[gesture.id])

    assert recorded_call(step, {gesture.id: gesture}) is None
    assert not writes(step, {gesture.id: gesture})


def test_the_write_the_click_caused_is_still_this_gestures_call() -> None:
    """The slowest real create in either store left its handler 59ms after the
    gesture. The rule has to keep every one of them: a write read as chatter is
    a write a dry run would send."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    assert gesture.at is not None
    gesture.requests = [
        _call(
            method="POST",
            url=f"{HOST}/data/WM/wm/customerTypes",
            request_id="save",
            started_at=gesture.at + 0.059,
            status=201,
        )
    ]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})
    assert call is not None and call.url.endswith("/customerTypes")


def test_a_call_exactly_at_the_window_is_still_the_gestures_own() -> None:
    """`K_CAUSED_S` is inclusive, and this is the only test that says so.

    The measured spread left no doubt about the middle -- real creates landed
    within 59ms, the nearest chatter at 667ms -- but the edge itself is a
    number nothing stands on, and the two mistakes cost differently: chatter
    read as a write parks a harmless step, a write read as chatter makes a dry
    run send it."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    assert gesture.at is not None
    gesture.requests = [
        _call(
            method="POST",
            url=f"{HOST}/data/WM/wm/customerTypes",
            request_id="slow",
            started_at=gesture.at + K_CAUSED_S,
            status=201,
        )
    ]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    assert recorded_call(step, {gesture.id: gesture}) is not None


def test_chatter_before_the_write_does_not_hide_the_write_behind_it() -> None:
    """Each call is passed over on its own, and the search goes on.

    Abandoning the loop at the first call the gesture did not cause would leave
    the real create unfound whenever the page happened to fire a keep-alive
    first -- which is the ordering three of the four misclassified steps in the
    real stores actually had."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    assert gesture.at is not None
    gesture.requests = [
        _call(
            method="POST",
            url=f"{HOST}/refs/data/api/v1/rp/admin/sessionKeepAlive",
            request_id="alive",
            started_at=gesture.at + 8.118,
            status=200,
        ),
        _call(
            method="POST",
            url=f"{HOST}/data/WM/wm/customerTypes",
            request_id="save",
            started_at=gesture.at + 0.016,
            status=201,
        ),
    ]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    call = recorded_call(step, {gesture.id: gesture})
    assert call is not None and call.url.endswith("/customerTypes")


def test_a_call_at_no_time_at_all_is_not_shown_to_be_uncaused() -> None:
    """The opposite of `confirming_read`, and for the same reason. There the
    claim is "after the write", so an untimed call cannot support it. Here the
    claim is "the gesture did not cause this", so an untimed call cannot
    support that either -- and the mistake this way round sends a write."""
    gesture = copy.deepcopy(next(g for g in _gestures() if g.requests))
    gesture.requests = [_call(method="POST", url=f"{HOST}/api/orders", started_at=None)]
    step = Step(order=0, says="save", system=None, cites=[gesture.id])

    assert writes(step, {gesture.id: gesture})


# --- which citation a step is aimed at ---------------------------------------


def _clicked(one: object, control: str) -> object:
    """One cited click, on a named control."""
    from sro.domain.observation.gesture import Component

    fresh = copy.deepcopy(one)
    fresh.id = f"ges_{control}"
    target = fresh.action.target
    assert target is not None
    fresh.action = replace(
        fresh.action,
        kind="click",
        value=None,
        target=replace(target, component=Component(query=control, xtype="button")),
    )
    return fresh


def test_a_step_that_carries_a_value_is_aimed_at_the_gesture_that_put_one() -> None:
    """Measured on the deployment 2026-09-22 at 16:09.

    `Delete a Customer Type` step 1 -- "Enter filter criteria to locate the
    target customer type" -- cited twenty-four gestures across three
    demonstrations, and the FIRST was a click on `removeCriterionButton`: the
    cross that clears a filter somebody left behind. The locator ladder was
    built for the cross, which exists only when a criterion is already there,
    so on a clean grid the ladder found nothing, the run fell to the vision
    rung and typed into nothing.

    The step is named for typing a filter and was aimed at the button that
    clears one.
    """
    typed = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    cross = _clicked(typed, "removeCriterionButton")
    by_id = {cross.id: cross, typed.id: typed}
    step = Step(
        order=0,
        says="Enter filter criteria",
        system=None,
        # The cleanup click first, exactly as mining listed them.
        cites=[cross.id, typed.id],
        parameters=["Customer Type"],
    )

    assert primary_gesture(step, by_id) is typed


def test_a_step_that_carries_nothing_is_aimed_at_its_first_citation() -> None:
    """A click, a navigation, a Save. `step.parameters` is the job's own word
    that a step takes a value, and where it says nothing the first citation is
    the answer -- which is what this has always returned."""
    typed = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    cross = _clicked(typed, "removeCriterionButton")
    by_id = {cross.id: cross, typed.id: typed}
    step = Step(order=0, says="clear the filter", system=None, cites=[cross.id, typed.id])

    assert primary_gesture(step, by_id) is cross


def _typed_into(one: object, item_id: str) -> object:
    """One cited typing, into a control the page calls `item_id`."""
    from sro.domain.observation.gesture import Component

    fresh = copy.deepcopy(one)
    fresh.id = f"ges_typed_{item_id}"
    target = fresh.action.target
    assert target is not None
    fresh.action = replace(
        fresh.action, target=replace(target, name="", component=Component(item_id=item_id))
    )
    return fresh


def test_a_step_is_aimed_at_the_typing_into_a_control_the_run_holds_a_value_for() -> None:
    """Measured on the deployment 2026-09-22 at 12:03.

    `Delete a Customer Type`, demonstrated again from a clean grid and mined
    fresh, came back with `parameters: []` on its filter step -- the second
    time -- and thirty-eight citations whose first targeted one was a click on
    no component at all. `step.parameters` is a model's answer and mining
    leaves it empty, so a rule gated on it never fired.

    The run knows better: it holds `filterComboBox` (the page's itemId, filed
    beside `Customer Type` by `_under_every_name`), and the step cites a typing
    into exactly that control.
    """
    base = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    typed = _typed_into(base, "filterComboBox")
    stray = _clicked(base, "searchField")
    by_id = {stray.id: stray, typed.id: typed}
    step = Step(order=0, says="Enter search criteria", system=None, cites=[stray.id, typed.id])

    assert primary_gesture(step, by_id, {"Customer Type", "filterComboBox"}) is typed


def test_a_typing_into_a_control_the_run_holds_nothing_for_changes_no_aim() -> None:
    """Holding a value is about THIS control. A step that declares nothing and
    types into a box the run has no value for is aimed where it always was."""
    base = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    typed = _typed_into(base, "filterComboBox")
    stray = _clicked(base, "searchField")
    by_id = {stray.id: stray, typed.id: typed}
    step = Step(order=0, says="Enter search criteria", system=None, cites=[stray.id, typed.id])

    assert primary_gesture(step, by_id, {"Department"}) is stray


def test_among_the_value_putting_citations_the_first_still_wins() -> None:
    """Order is otherwise untouched: a step that types into two boxes is aimed
    exactly where it was."""
    every = [g for g in _gestures() if g.action.kind == "type" and not g.action.secret]
    first, second = every[0], copy.deepcopy(every[0])
    second.id = "ges_second_box"
    by_id = {first.id: first, second.id: second}
    step = Step(
        order=0,
        says="type both",
        system=None,
        cites=[first.id, second.id],
        parameters=["a", "b"],
    )

    assert primary_gesture(step, by_id) is first


def _row_checker() -> object:
    """A click on a grid row's checkbox, exactly as the deployment recorded it."""
    from sro.domain.observation.gesture import Component

    base = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    fresh = copy.deepcopy(base)
    fresh.id = "ges_row_checker"
    target = fresh.action.target
    assert target is not None
    fresh.action = replace(
        fresh.action,
        kind="click",
        value=None,
        target=replace(
            target,
            name=None,
            role="presentation",
            text=None,
            test_id=None,
            css_path=(
                "td#ext-gen5745 > div.x-grid-cell-inner > div.x-grid-row-checker:nth-of-type(2)"
            ),
            component=Component(
                query="rpFilterableGrid#masterdata-customer-existingcustomertypes-grid gridview",
                xtype="gridview",
            ),
        ),
    )
    return fresh


def test_a_click_inside_a_view_is_aimed_at_the_row_not_the_view() -> None:
    """Measured on the deployment 2026-09-22 at 13:54. `Delete a Customer Type`
    step 2 selected the row by clicking its checkbox, whose component is the
    grid's `gridview`. The component rung matched the whole view, the click
    landed on it, nothing was selected and Delete stayed disabled -- twice.

    The recorded leaf, with its render-order id and position struck, scoped to
    the view, goes first."""
    ladder = locators_for(_row_checker())

    assert ladder[0].as_payload() == {
        "strategy": "css_path",
        "query": "div.x-grid-row-checker",
        "within": "rpFilterableGrid#masterdata-customer-existingcustomertypes-grid gridview",
        "visible_only": True,
    }
    assert ladder[1].strategy == "component", "the view itself is still a rung below it"


def test_a_control_that_is_not_a_view_keeps_its_ladder() -> None:
    """A button, a text box, a combobox: the component IS the control, and the
    first rung is what it always was -- even where its recorded leaf carries a
    class that would survive a render."""
    from sro.domain.observation.gesture import Component

    button = _row_checker()
    target = button.action.target
    assert target is not None
    button.action = replace(
        button.action,
        target=replace(
            target,
            css_path="a#button-1624 > span.x-btn-inner",
            component=Component(
                query="rpCriterionView button#removeCriterionButton", xtype="button"
            ),
        ),
    )

    assert locators_for(button)[0].strategy == "component"
