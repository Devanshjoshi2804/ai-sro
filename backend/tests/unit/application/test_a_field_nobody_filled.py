"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

import json

from sro.application.induction import binding, jsonutil
from sro.application.induction.diff import Difference, differences, parameterise
from sro.application.induction.sites import JsonBodySite
from sro.domain.recording.events import ActionKind, InputAction
from tests import factories as f

URL = "https://wms.test/data/WM/wm/workareas"


def test_an_empty_value_is_not_a_different_shape() -> None:
    filled = {"workArea": "TWOTEST", "deltaPriority": 1, "distanceThreshold": ""}
    skipped = {"workArea": "THREE TE", "deltaPriority": None, "distanceThreshold": ""}

    assert jsonutil.same_shape(filled, skipped) is True


def test_a_key_one_run_does_not_send_is_still_a_different_shape() -> None:
    """The rule this relaxes exists for a reason. A key present in one body and
    absent from the other is two different requests, not one optional field."""
    with_key = {"workArea": "TWOTEST", "deltaPriority": 1}
    without_key = {"workArea": "THREE TE"}

    assert jsonutil.same_shape(with_key, without_key) is False


def test_two_kinds_of_filled_value_still_disagree() -> None:
    """Relaxing null against anything is the whole change. A number against a
    string is a flow that diverged, and stays one."""
    assert jsonutil.same_shape({"qty": 5}, {"qty": "five"}) is False


def test_a_filled_group_and_a_null_group_are_the_same_shape() -> None:
    """A whole group can be left alone the same way one field can: null for
    the group's key rather than null for every key inside it."""
    assert jsonutil.same_shape({"extra": {"bar": 1}}, {"extra": None}) is True


def _run(body: dict[str, object]) -> tuple:
    request = f.request(method="POST", url=URL, request_body=f.body(json.dumps(body)))
    return (f.frame(0, requests=(request,)),)


def test_a_field_filled_once_becomes_a_difference_with_its_absent_form() -> None:
    """`null` and `""` are both absence, and which one this field uses is the
    application's business -- so the diff reads it off the run that skipped
    it rather than choosing one."""
    run_a = _run({"workArea": "TWOTEST", "deltaPriority": 1})
    run_b = _run({"workArea": "TWOTEST", "deltaPriority": None})

    found = differences(run_a, run_b)

    assert found == [
        Difference(
            step_index=0,
            site=JsonBodySite("/deltaPriority"),
            value_a="1",
            value_b="",
            absent_as="null",
        )
    ]


def test_a_field_filled_once_is_optional_and_remembers_what_empty_looked_like() -> None:
    run_a = _run({"workArea": "TWOTEST", "deltaPriority": 1})
    run_b = _run({"workArea": "TWOTEST", "deltaPriority": None})

    parameters = parameterise(run_a, run_b).parameters

    assert len(parameters) == 1
    parameter = parameters[0]
    assert parameter.optional is True
    assert parameter.absent_as == "null"
    assert parameter.observed_values == ("1",), "an absence is not a value somebody observed"


def test_a_group_left_null_is_the_same_optional_field_one_level_down() -> None:
    """One run fills a nested group; the other sends null for the whole thing
    rather than for the field inside it. The leaf that varies is two pointers
    deep, but what "left alone" looked like is still the empty group, not a
    missing leaf -- so this reads the group's null, not a `KeyError`."""
    run_a = _run({"workArea": "TWOTEST", "extra": {"bar": 1}})
    run_b = _run({"workArea": "TWOTEST", "extra": None})

    found = differences(run_a, run_b)

    assert found == [
        Difference(
            step_index=0,
            site=JsonBodySite("/extra/bar"),
            value_a="1",
            value_b="",
            absent_as="null",
        )
    ]


def test_a_group_left_null_is_optional_however_the_runs_happen_to_be_ordered() -> None:
    """Which recording landed as A and which as B is an accident of storage
    order, not something an operator controls -- so the mirror of the case
    above has to resolve the same way, not raise. Here it is `document_a`
    that sent null for the whole group and `document_b` that filled it in."""
    run_a = _run({"workArea": "TWOTEST", "extra": None})
    run_b = _run({"workArea": "TWOTEST", "extra": {"bar": 1}})

    found = differences(run_a, run_b)

    assert found == [
        Difference(
            step_index=0,
            site=JsonBodySite("/extra/bar"),
            value_a="",
            value_b="1",
            absent_as="null",
        )
    ]


def test_a_typed_value_is_bound_to_the_field_it_filled() -> None:
    typing = f.frame(
        0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="twoTEST")
    )
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"workArea": "TWOTEST"}')),))

    assert binding.key_filled_by(typing, saving) == "/workArea"


def test_a_form_is_allowed_to_tidy_what_it_was_given() -> None:
    """The work area name field uppercases as you type. Exact comparison would
    fail to bind the one field the whole task is named for."""
    typing = f.frame(
        0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value=" 1 ")
    )
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"voiceCode": 1}')),))

    assert binding.key_filled_by(typing, saving) == "/voiceCode"


def test_a_value_that_could_be_two_fields_is_bound_to_neither() -> None:
    """Two keys holding "1" cannot say which one the keystroke filled, and a
    step made conditional on the wrong field is a step that silently stops
    happening."""
    typing = f.frame(0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="1"))
    saving = f.frame(
        1, requests=(f.request(request_body=f.body('{"voiceCode": 1, "priority": 1}')),)
    )

    assert binding.key_filled_by(typing, saving) is None


def test_a_click_fills_nothing() -> None:
    clicking = f.frame(0, action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint()))
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"workArea": "X"}')),))

    assert binding.key_filled_by(clicking, saving) is None
