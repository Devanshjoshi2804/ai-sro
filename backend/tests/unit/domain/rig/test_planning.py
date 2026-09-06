"""Ported from `new_agent_arch/tests/test_planner.py`, plus the schema walker
from its `test_entry.py`.

Left for plan 3, every one of them a `plan_step` or `plan_by_sight` test and so
a test of the model call this module deliberately does not carry:
`test_a_ui_plan_carries_the_evidence_locators_not_the_models`,
`test_the_values_the_run_was_given_are_what_the_model_sees_not_the_recorded_ones`,
`test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped`,
`test_an_http_plan_whose_body_the_store_never_kept_is_downgraded_to_the_interface`,
`test_a_model_that_could_not_answer_plans_nothing_and_says_why`,
`test_a_kind_the_protocol_does_not_have_is_planned_as_nothing`,
`test_a_retry_carries_the_failure_and_the_second_screenshot`,
`test_an_http_plan_whose_url_carries_a_struck_out_credential_is_downgraded`,
`test_every_way_out_hands_back_the_reading_that_paid_for_it`,
`test_a_navigate_with_nowhere_to_go_is_not_a_navigate`,
`test_the_why_on_the_plan_is_the_models_own_and_empty_when_it_gave_none`,
`test_a_step_that_only_cites_a_scroll_is_still_planned_from_it`,
`test_the_action_is_the_models_when_the_protocol_has_it_and_the_gestures_when_not`,
`test_a_value_is_carried_for_every_action_that_takes_one_and_for_no_other`,
`test_with_no_value_from_the_run_or_the_model_the_recorded_one_stands`,
`test_a_recorded_call_with_no_body_is_replayed_as_it_was`,
`test_an_http_plan_carries_the_body_the_operator_sent`,
`test_an_http_plan_for_a_step_whose_evidence_made_no_call_plans_nothing`,
`test_the_model_is_told_where_the_step_was_demonstrated_and_under_what_effort`,
`test_a_rescue_is_shown_the_page_the_failed_attempt_left_behind`,
`test_a_first_attempt_carries_no_second_picture`,
`test_the_failed_attempts_picture_is_named_by_its_position`,
`test_a_replayed_call_still_carries_the_answer_that_planned_it`,
`test_the_sight_rung_is_asked_with_the_screen_its_size_and_the_demonstrated_control`,
`test_the_corner_of_the_screen_is_on_it_and_its_far_edge_is_not`,
`test_no_picture_no_size_or_no_answer_is_no_plan`,
`test_nothing_to_type_is_no_plan_and_a_press_carries_no_value`.

The rules those tests reach `plan_step` to exercise -- the value rule and the
replayability rule -- are asserted directly below instead, so they are pinned
now rather than in whichever plan brings the model call across.
"""

import importlib
import pkgutil
from dataclasses import replace

import sro.domain
from sro.domain.execution.planning import (
    PLAN_SCHEMA,
    SIGHT_ACTIONS,
    SIGHT_SCHEMA,
    unreplayable,
    value_for,
)
from sro.domain.observation.gesture import Body, Call, Gesture
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures


def _typed() -> Gesture:
    return next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)


def _step(gesture: Gesture) -> Step:
    return Step(order=0, says="type", system=None, cites=[gesture.id])


def test_the_schema_puts_why_last_and_kind_first() -> None:
    """Decide before explaining: identifying the command before composing the
    reason measurably beats composing first."""
    properties = PLAN_SCHEMA["properties"]
    assert isinstance(properties, dict)
    assert list(properties) == ["kind", "action", "value", "url", "why"]


def test_the_runs_value_beats_the_models_word_which_beats_the_recorded_one() -> None:
    """The run's values win: they are what the person asked for. Under them the
    model's word, and under that what the operator actually typed."""
    gesture = _typed()
    step = _step(gesture)

    assert value_for(step, gesture, {"clientCode": "THIRD"}, "SAID") == "THIRD"
    assert value_for(step, gesture, {}, "SAID") == "SAID"
    assert value_for(step, gesture, {}, None) == gesture.action.value


def test_a_secret_gesture_carries_no_value_from_anywhere() -> None:
    """The second belt `trim.is_secret` wears, and for the same reason: the
    wire validator that nulled the value does not re-run when a nested Target
    is mutated afterwards."""
    gesture = _typed()
    target = gesture.action.target
    assert target is not None
    step = _step(gesture)

    flagged = replace(gesture, action=replace(gesture.action, secret=True))
    assert value_for(step, flagged, {"clientCode": "THIRD"}, "SAID") is None

    mutated = replace(gesture, action=replace(gesture.action, target=replace(target, secret=True)))
    assert value_for(step, mutated, {"clientCode": "THIRD"}, "SAID") is None


def _call(body: Body | None = None) -> Call:
    return Call(method="POST", url="https://wms.example/api/save", request_body=body)


def test_a_body_the_store_never_kept_is_not_replayable() -> None:
    """Offloaded to a blob: the call would arrive with nothing where the
    payload was."""
    assert unreplayable(_call(Body(text=None, blob_uri="s3://bodies/ges_9de89")))


def test_a_body_a_field_was_struck_out_of_is_not_replayable() -> None:
    assert unreplayable(_call(Body(text=None, redacted_fields=("password",))))
    assert unreplayable(_call(Body(text=f'{{"password": "{REDACTED}"}}')))


def test_a_url_carrying_a_struck_out_credential_is_not_replayable() -> None:
    """The marker's own text would go out where the cookie was."""
    assert unreplayable(Call(method="GET", url=f"https://wms.example/beacon?session={REDACTED}"))


def test_a_call_with_no_body_at_all_is_replayable() -> None:
    """There is nothing to get wrong."""
    assert unreplayable(_call()) is False
    assert unreplayable(_call(Body(text='{"dock": "D3"}'))) is False


def test_the_sight_schema_offers_only_the_actions_a_point_can_take() -> None:
    """No select: `performAtInPage` has no way to choose an option at a point,
    and an action the browser cannot take is a step that stops. SIGHT_ACTIONS
    is what the answer is checked against, so it has to be the same three."""
    properties = SIGHT_SCHEMA["properties"]
    assert isinstance(properties, dict)
    action = properties["action"]
    assert isinstance(action, dict)

    assert action["enum"] == ["click", "type", "press"]
    assert frozenset(action["enum"]) == SIGHT_ACTIONS


def test_no_schema_in_the_package_uses_what_the_developer_api_refuses() -> None:
    """`additionalProperties` is refused by the Gemini Developer API with a
    400 -- "only supported in Gemini Enterprise Agent Platform mode". The
    chat door shipped with one and had never met the real API; every schema
    the domain asks under is walked here so the next one cannot."""

    def walk(node: object, at: str) -> list[str]:
        found = []
        if isinstance(node, dict):
            if "additionalProperties" in node:
                found.append(at)
            for k, v in node.items():
                found += walk(v, f"{at}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                found += walk(v, f"{at}[{i}]")
        return found

    offenders: list[str] = []
    walked = 0
    for info in pkgutil.walk_packages(sro.domain.__path__, prefix="sro.domain."):
        module = importlib.import_module(info.name)
        for name in dir(module):
            if name.endswith("_SCHEMA") and isinstance(getattr(module, name), dict):
                walked += 1
                offenders += walk(getattr(module, name), f"{info.name}.{name}")
    assert offenders == [], offenders
    assert walked, "the walker found no schema at all, which is how it stops being a test"
