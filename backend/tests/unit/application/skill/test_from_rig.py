"""A workflow the rig mined, as steps this system can run.

Measured over the eight workflows mined from 170 hours of real capture: every
one of 66 steps produces at least one action, and of the 165 actions those
steps make, 118 resolve to a component query -- the framework's own handle
rather than a DOM path. 33 of the rest are scrolls, which have no target and
so no locator; 13 fall to text, css path or role-and-name.
"""

from sro.application.skill.from_rig import (
    locators_for,
    plan_for_gesture,
    plans_for_step,
    plans_for_workflow,
)
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import LocatorStrategy

EXTJS = {
    "role": "textbox",
    "name": "Activity Code",
    "cssPath": "div#x > input",
    "component": {
        "xtype": "textfield",
        "itemId": "activityCode",
        "query": "container textfield#activityCode",
    },
}


def test_the_ladder_puts_the_framework_first() -> None:
    """LocatorStrategy's own order: a component query is what the application's
    code uses to find the control, and a css path is the last resort."""
    ladder = locators_for(EXTJS)

    assert [rung.strategy for rung in ladder] == [
        LocatorStrategy.COMPONENT,
        LocatorStrategy.ROLE_AND_NAME,
        LocatorStrategy.CSS_PATH,
    ]
    assert ladder[0].query.raw == "container textfield#activityCode"


def test_an_item_id_alone_is_still_a_query_in_the_frameworks_language() -> None:
    """A recorder that reached the framework enough to report an itemId but not
    a query has still said where the control is."""
    ladder = locators_for(
        {"name": "Save", "role": "button", "component": {"xtype": "button", "itemId": "saveButton"}}
    )

    assert ladder[0].strategy is LocatorStrategy.COMPONENT
    assert ladder[0].query.raw == "#saveButton"


def test_a_scroll_is_a_step_with_nowhere_to_point() -> None:
    """It carries no target, because you scroll a page and not an element --
    and a driver can still perform it. UiPlan says so itself: `replayable` is
    false only for actions that NEED a target and have no locator, and scroll
    is not one of those. A bridge that dropped it would lose a real step."""
    plan = plan_for_gesture({"kind": "scroll", "value": "0"})

    assert plan is not None
    assert plan.action is ActionKind.SCROLL
    assert plan.locators == (), "there is nothing to find"
    assert plan.replayable, "which does not stop a driver scrolling"


def test_an_action_needing_a_target_without_one_is_refused() -> None:
    """UiPlan would refuse it anyway. Refusing here answers 'why is there no
    plan for that step' without building one that gets rejected."""
    assert plan_for_gesture({"kind": "click", "target": {"bounds": {"x": 1.0}}}) is None


def test_a_kind_neither_side_has_heard_of_is_a_miss_not_a_crash() -> None:
    assert plan_for_gesture({"kind": "levitate", "target": EXTJS}) is None


def test_what_was_typed_becomes_a_template() -> None:
    """A run may be asked to type a different one, which is what makes this a
    skill rather than a recording."""
    plan = plan_for_gesture({"kind": "type", "value": "TEST1", "target": EXTJS})

    assert plan is not None
    assert plan.action is ActionKind.TYPE
    assert plan.value is not None and plan.value.raw == "TEST1"
    assert plan.replayable


def test_a_step_that_cites_only_scrolls_still_runs_them() -> None:
    """`Scroll down the portal screen` is a real step of a real workflow here,
    and a bridge that produced nothing for it would offer a job missing a step
    it was described as having."""
    gestures = {"g1": {"kind": "scroll", "value": "0"}}
    step = {"order": 0, "says": "Scroll down the portal screen.", "cites": ["g1"]}

    pairs = plans_for_workflow({"steps": [step]}, gestures)

    assert len(pairs) == 1
    assert [plan.action for plan in pairs[0][1]] == [ActionKind.SCROLL]


def test_a_step_runs_every_gesture_it_cites_in_order() -> None:
    gestures = {
        "g1": {"kind": "scroll", "value": "0"},
        "g2": {"kind": "click", "target": EXTJS},
        "g3": {"kind": "type", "value": "TEST1", "target": EXTJS},
    }
    step = {"order": 0, "says": "Enter the code.", "cites": ["g1", "g2", "g3"]}

    plans = plans_for_step(step, gestures)

    assert [plan.action for plan in plans] == [
        ActionKind.SCROLL,
        ActionKind.CLICK,
        ActionKind.TYPE,
    ]


def test_a_citation_naming_evidence_nobody_has_is_skipped() -> None:
    """checks.validate refuses a workflow citing evidence that does not exist,
    so arriving here with one means the store moved underneath."""
    step = {"order": 0, "says": "x", "cites": ["ges_gone", "g2"]}

    plans = plans_for_step(step, {"g2": {"kind": "click", "target": EXTJS}})

    assert len(plans) == 1


def test_steps_are_run_in_the_order_the_workflow_gives_them() -> None:
    gestures = {"g": {"kind": "click", "target": EXTJS}}
    out_of_order = [
        {"order": 2, "says": "third", "cites": ["g"]},
        {"order": 0, "says": "first", "cites": ["g"]},
        {"order": 1, "says": "second", "cites": ["g"]},
    ]

    pairs = plans_for_workflow({"steps": out_of_order}, gestures)

    assert [step["says"] for step, _ in pairs] == ["first", "second", "third"]


WORKFLOW_WITH_A_PARAMETER = {
    "steps": [{"order": 0, "says": "Enter the code.", "cites": ["g"]}],
    "parameters": [{"name": "activityCode", "seen_values": ["TEST1", "TEST2"]}],
}


def test_a_value_the_job_varies_becomes_the_name_it_varies_under() -> None:
    """This is what makes it a skill rather than a recording: a run can be
    asked for a different code."""
    gestures = {"g": {"kind": "type", "value": "TEST1", "target": EXTJS}}

    plans = plans_for_workflow(WORKFLOW_WITH_A_PARAMETER, gestures)[0][1]

    assert plans[0].value is not None
    assert plans[0].value.raw == "$activityCode"
    assert plans[0].placeholders == {"activityCode"}


def test_a_value_nobody_has_seen_vary_stays_literal() -> None:
    """It is part of the job until evidence says otherwise. Guessing which
    literals are really inputs is the thing two doings exist to avoid -- one
    doing of `Create Work Activity TEST1` cannot say whether TEST1 names this
    activity or every activity."""
    gestures = {"g": {"kind": "type", "value": "Released", "target": EXTJS}}

    plans = plans_for_workflow(WORKFLOW_WITH_A_PARAMETER, gestures)[0][1]

    assert plans[0].value is not None
    assert plans[0].value.raw == "Released"
    assert plans[0].placeholders == frozenset()


def test_a_workflow_with_no_parameters_binds_nothing() -> None:
    """Which is every workflow mined from the real corpus so far: one doing of
    each job, and one doing names no parameters."""
    gestures = {"g": {"kind": "type", "value": "TEST1", "target": EXTJS}}
    workflow = {"steps": [{"order": 0, "says": "x", "cites": ["g"]}], "parameters": []}

    plans = plans_for_workflow(workflow, gestures)[0][1]

    assert plans[0].value is not None and plans[0].value.raw == "TEST1"


def test_an_order_that_is_not_a_number_does_not_crash_the_sort() -> None:
    """Every other field here goes through `_text` or `_mapping`; `order` went
    through neither, and the `type: ignore` on the sort key was mypy having
    already said so. A workflow whose orders mix `1` and `"2"` -- which is
    ordinary JSON, from a store that moved or a model that quoted a number --
    raised TypeError and took the whole bridge down.
    """
    gestures = {"g": {"kind": "click", "target": EXTJS}}
    mixed = [
        {"order": "2", "says": "third", "cites": ["g"]},
        {"order": 1, "says": "second", "cites": ["g"]},
        {"order": 0.5, "says": "first", "cites": ["g"]},
    ]

    pairs = plans_for_workflow({"steps": mixed}, gestures)

    assert [step["says"] for step, _ in pairs] == ["first", "second", "third"]


def test_orders_that_are_all_strings_sort_by_number_and_not_by_spelling() -> None:
    """The quieter half. All-string orders never raised -- they sorted
    lexicographically, putting step 10 before step 2 and producing a plan that
    runs the job in the wrong order without a single error to notice."""
    gestures = {"g": {"kind": "click", "target": EXTJS}}
    steps = [{"order": str(n), "says": str(n), "cites": ["g"]} for n in (10, 2, 1)]

    pairs = plans_for_workflow({"steps": steps}, gestures)

    assert [step["says"] for step, _ in pairs] == ["1", "2", "10"]


def test_an_order_nobody_can_read_sorts_last_rather_than_first() -> None:
    """A missing or unreadable order defaulted to 0, which put the step the
    workflow said least about at the front of the job."""
    gestures = {"g": {"kind": "click", "target": EXTJS}}
    steps = [
        {"order": None, "says": "unreadable", "cites": ["g"]},
        {"order": 3, "says": "third", "cites": ["g"]},
    ]

    pairs = plans_for_workflow({"steps": steps}, gestures)

    assert [step["says"] for step, _ in pairs] == ["third", "unreadable"]


OTHER_CONTROL = {
    "role": "combobox",
    "name": "Status",
    "cssPath": "div#y > input",
    "component": {"xtype": "combo", "itemId": "statusCombo", "query": "combo#statusCombo"},
}

TWO_PARAMETERS = {
    "steps": [{"order": 0, "says": "Set both.", "cites": ["a", "b"]}],
    "parameters": [
        {"name": "activityCode", "seen_values": ["Active", "TEST2"]},
        {"name": "statusCombo", "seen_values": ["Active", "Closed"]},
    ],
}


def test_a_value_binds_only_to_the_control_the_parameter_is_named_after() -> None:
    """Binding on the value alone binds by coincidence.

    Two parameters that were each given `Active` on some doing collide in a
    value-keyed map, and `setdefault` hands both to whichever name sorts first
    -- so the status combo would be told to type `$activityCode`. The run then
    supplies the wrong input to the wrong field, and nothing anywhere reports
    a problem.
    """
    gestures = {
        "a": {"kind": "type", "value": "Active", "target": EXTJS},
        "b": {"kind": "type", "value": "Active", "target": OTHER_CONTROL},
    }

    plans = plans_for_workflow(TWO_PARAMETERS, gestures)[0][1]

    assert plans[0].value is not None and plans[0].value.raw == "$activityCode"
    assert plans[1].value is not None and plans[1].value.raw == "$statusCombo"


def test_a_constant_that_happens_to_equal_a_parameters_value_stays_literal() -> None:
    """The worse half of the same defect. A field nobody has seen vary, typed
    with a string some other parameter was once given, became a `$name` the
    runner substitutes -- turning a fixed part of the job into an input."""
    gestures = {
        "a": {"kind": "type", "value": "Active", "target": EXTJS},
        "b": {
            "kind": "type",
            "value": "Active",
            "target": {"role": "textbox", "name": "Notes", "cssPath": "div#z > input"},
        },
    }

    plans = plans_for_workflow(TWO_PARAMETERS, gestures)[0][1]

    assert plans[1].value is not None and plans[1].value.raw == "Active", "not a parameter"


def test_a_dollar_in_a_recorded_value_is_a_dollar_and_not_a_parameter() -> None:
    """`Template` is `string.Template`, so `$` starts a placeholder. A price,
    a shell fragment or a template the operator typed literally would report
    itself as a parameter the plan needs, and `render` then raises KeyError or
    substitutes something nobody typed. Nothing is a parameter here unless a
    binding says so."""
    gestures = {"g": {"kind": "type", "value": "Total $AMOUNT due", "target": EXTJS}}

    plans = plans_for_workflow({"steps": [{"order": 0, "says": "x", "cites": ["g"]}]}, gestures)

    plan = plans[0][1][0]
    assert plan.value is not None
    assert plan.placeholders == frozenset(), "it names no parameter"
    assert plan.value.render({}) == "Total $AMOUNT due", "and renders back to itself"


def test_a_dollar_in_a_css_path_is_not_a_parameter_either() -> None:
    """Same rule, the other string. A locator is never a binding."""
    target = {"role": "textbox", "name": "Code", "cssPath": "div[data-x='$y'] > input"}
    plan = plan_for_gesture({"kind": "click", "target": target})

    assert plan is not None
    assert all(locator.query.placeholders == frozenset() for locator in plan.locators)
