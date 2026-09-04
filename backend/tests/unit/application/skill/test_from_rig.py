"""A workflow the rig mined, as steps this system can run.

Measured over the eight workflows mined from 170 hours of real capture: every
one of 66 steps produces at least one action, and 118 of 132 actions resolve to
a component query -- the framework's own handle rather than a DOM path.
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
