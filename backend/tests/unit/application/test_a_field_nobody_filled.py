"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    ExecutionRequest,
    NotRunnable,
    StartRun,
    _check_runnable,
)
from sro.application.execution.self_heal import Healed
from sro.application.induction import binding, jsonutil
from sro.application.induction.diff import (
    Difference,
    align,
    differences,
    parameterise,
)
from sro.application.induction.errors import InductionFailed
from sro.application.induction.sites import JsonBodySite, UrlQuerySite, substitute_body
from sro.domain.execution.diagnosis import Remedy
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import HeaderPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUiDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

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
    """Same request, different value in it -- so `same_shape` says yes. What
    the diff can do with it is a different question, answered below: it
    refuses, because the absent form of a group is not the absent form of the
    leaves inside it."""
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
            filled_as="number",
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
    assert parameter.unquoted_as == "number", "what the run that filled it sent"
    assert parameter.observed_values == ("1",), "an absence is not a value somebody observed"
    assert parameter.is_the_body is False, "a leaf inside the body, not the body"


def test_a_body_that_is_not_json_is_one_parameter_that_is_the_body() -> None:
    """A SOAP body is parameterised whole -- the diff has no leaves to address
    in it -- so the value that fills it is the body rather than a value inside
    one. Recorded on the parameter, because execution has to know not to
    escape it into a JSON string that is not there, and not to refuse it for
    the quotes and newlines every envelope carries."""
    envelopes = [f'<?xml version="1.0"?><Release id="W-{n}"/>' for n in ("42", "43")]
    runs = [
        (
            f.frame(
                0,
                requests=(
                    f.request(
                        method="POST",
                        url=URL,
                        request_body=f.body(envelope),
                    ),
                ),
            ),
        )
        for envelope in envelopes
    ]

    parameters = parameterise(*runs).parameters

    assert len(parameters) == 1
    assert parameters[0].is_the_body is True
    assert parameters[0].observed_values == tuple(envelopes)
    assert parameters[0].rejects(envelopes[0]) is None, "its own recorded value must be sendable"


def test_a_group_one_run_left_empty_is_refused_rather_than_guessed_at() -> None:
    """The absent form of an *ancestor* is not the absent form of a leaf.

    Run B sent `"lines": null`; it never sent a line item at all. Handing that
    `null` down to `/lines/0/sku` and `/lines/0/qty` individually emitted
    `{"ref":"${ref}","lines":[{"sku":${sku},"qty":${qty}}]}`, and a run
    supplying neither sent `{"lines":[{"sku":null,"qty":null}]}` -- a shape
    neither demonstration sent, and a blank order line in a WMS that takes it.

    One optional parameter holding the whole group would be the other honest
    answer, and it is a parameter whose value is an object: no rule here can
    check one against the slot it goes in. So the pair refuses, in a sentence.
    """
    run_a = _run({"ref": "R1", "lines": [{"sku": "ABC", "qty": 2}]})
    run_b = _run({"ref": "R2", "lines": None})

    with pytest.raises(InductionFailed, match="one sent a group there and the other left it"):
        differences(run_a, run_b)


def test_a_group_left_empty_is_refused_however_the_runs_happen_to_be_ordered() -> None:
    """Which recording landed as A and which as B is an accident of storage
    order, not something an operator controls, so the mirror has to resolve the
    same way. Here it is `document_a` that sent null for the whole group."""
    run_a = _run({"workArea": "TWOTEST", "extra": None})
    run_b = _run({"workArea": "TWOTEST", "extra": {"bar": 1}})

    with pytest.raises(InductionFailed, match="/extra"):
        differences(run_a, run_b)


def test_one_leaf_under_an_emptied_group_is_refused_too() -> None:
    """The single-leaf case looks harmless and is the same bug: nothing sent
    `{"extra":{"bar":null}}` either. Pinned separately because it is the shape
    the first version of this rule was written against and passed."""
    run_a = _run({"workArea": "TWOTEST", "extra": {"bar": 1}})
    run_b = _run({"workArea": "TWOTEST", "extra": None})

    with pytest.raises(InductionFailed, match="a skill cannot yet express one"):
        differences(run_a, run_b)


def test_a_field_neither_run_filled_is_not_a_difference_at_all() -> None:
    """`null` in one run and `""` in the other are two spellings of the same
    thing: nobody filled this. Their string forms differ, though, so the diff
    read them as a value that varies and emitted a required parameter with
    observed values `("", "")` -- nothing an operator could sensibly supply,
    and required, so every run that left it out was refused. An absence is not
    a value on either side of the comparison."""
    run_a = _run({"workArea": "TWOTEST", "note": None})
    run_b = _run({"workArea": "TWOTEST", "note": ""})

    assert differences(run_a, run_b) == []
    assert parameterise(run_a, run_b).parameters == ()


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


def test_a_control_that_names_its_own_field_breaks_the_tie() -> None:
    """The evidence of 2026-08-27 sends `voiceCode` "1" beside `deltaPriority`
    1, so the rule above binds the Delta Priority keystroke to neither -- and
    the one field the whole pair turns on became unfillable. The control is not
    silent about this: an ExtJS field is named for the key it posts under, and
    where exactly one of the tied keys is the field's own name, nothing is
    being guessed."""
    typing = f.frame(
        0,
        action=InputAction(
            kind=ActionKind.TYPE,
            target=f.fingerprint(
                role="textbox",
                accessible_name="Delta Priority",
                attributes={"name": "deltaPriority"},
            ),
            value="1",
        ),
    )
    saving = f.frame(
        1, requests=(f.request(request_body=f.body('{"voiceCode": "1", "deltaPriority": 1}')),)
    )

    assert binding.key_filled_by(typing, saving) == "/deltaPriority"


def test_a_control_named_after_neither_tied_field_still_binds_to_neither() -> None:
    typing = f.frame(
        0,
        action=InputAction(
            kind=ActionKind.TYPE,
            target=f.fingerprint(attributes={"name": "somethingElse"}),
            value="1",
        ),
    )
    saving = f.frame(
        1, requests=(f.request(request_body=f.body('{"voiceCode": "1", "deltaPriority": 1}')),)
    )

    assert binding.key_filled_by(typing, saving) is None


def test_a_click_fills_nothing() -> None:
    clicking = f.frame(0, action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint()))
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"workArea": "X"}')),))

    assert binding.key_filled_by(clicking, saving) is None


def test_whitespace_typed_is_not_evidence_it_filled_anything() -> None:
    """A keystroke that typed nothing but whitespace is not proof it filled
    the field a form happened to send back empty -- tidying must not turn
    "typed nothing" into a match for "left blank"."""
    typing = f.frame(0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value=" "))
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"note": ""}')),))

    assert binding.key_filled_by(typing, saving) is None


def test_the_word_none_does_not_bind_to_a_json_null() -> None:
    """`str(None)` renders "None", which case-folds to the English word
    "none" -- close enough to fool a naive comparison into binding a real
    keystroke to a field nobody touched."""
    typing = f.frame(
        0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="none")
    )
    saving = f.frame(1, requests=(f.request(request_body=f.body('{"workArea": null}')),))

    assert binding.key_filled_by(typing, saving) is None


def test_a_failed_write_is_not_evidence_of_what_it_would_have_filled() -> None:
    """A write the system rejected is not the write a typed value ended up
    in -- binding to a failed call points a step at whatever the retry
    changed, not at what actually happened."""
    typing = f.frame(
        0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="TWOTEST")
    )
    saving = f.frame(
        1,
        requests=(
            f.request(
                status=500,
                status_text="Internal Server Error",
                request_body=f.body('{"workArea": "TWOTEST"}'),
            ),
        ),
    )

    assert binding.key_filled_by(typing, saving) is None


def test_a_frame_with_two_writes_is_not_bound_to_only_the_first() -> None:
    """Before `explode` splits a gesture into steps, one frame can carry two
    real writes -- a Save that creates a record and then sets its address.
    The field that matters is not always the first call the browser sent."""
    typing = f.frame(
        0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="TWOTEST")
    )
    saving = f.frame(
        1,
        requests=(
            f.request(request_id="req-1", request_body=f.body('{"priority": 1}')),
            f.request(request_id="req-2", request_body=f.body('{"workArea": "TWOTEST"}')),
        ),
    )

    assert binding.key_filled_by(typing, saving) == "/workArea"


_WORK_AREA = f.fingerprint(node_id="work-area", accessible_name="Work Area")
_DELTA_PRIORITY = f.fingerprint(node_id="delta-priority", accessible_name="Delta Priority")
_ZONE = f.fingerprint(node_id="zone", accessible_name="Zone")
_SAVE = f.fingerprint(node_id="save", accessible_name="Create work area")


def test_a_step_the_other_run_skipped_does_not_refuse_the_pair() -> None:
    """The two work areas. One run typed a Delta Priority and the other did
    not, and both created a work area."""
    filled = (
        f.frame(
            0, action=InputAction(kind=ActionKind.TYPE, target=_WORK_AREA, value="ONE"), requests=()
        ),
        f.frame(
            1,
            action=InputAction(kind=ActionKind.TYPE, target=_DELTA_PRIORITY, value="1"),
            requests=(),
        ),
        f.frame(
            2,
            action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
            requests=(
                f.request(
                    method="POST",
                    url=URL,
                    request_body=f.body('{"workArea": "ONE", "deltaPriority": 1}'),
                ),
            ),
        ),
    )
    skipped = (
        f.frame(
            0, action=InputAction(kind=ActionKind.TYPE, target=_WORK_AREA, value="TWO"), requests=()
        ),
        f.frame(
            1,
            action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
            requests=(
                f.request(
                    method="POST",
                    url=URL,
                    request_body=f.body('{"workArea": "TWO", "deltaPriority": null}'),
                ),
            ),
        ),
    )

    paired = align(filled, skipped)

    assert len(paired) == 2, "the pair was refused, or the skipped step was kept"


def test_a_step_that_filled_something_the_other_run_did_not_send_still_refuses() -> None:
    """A key in one body and not the other is two different requests. The
    relaxation is for a field both runs carry and one leaves alone."""
    filled = (
        f.frame(
            0, action=InputAction(kind=ActionKind.TYPE, target=_WORK_AREA, value="ONE"), requests=()
        ),
        f.frame(1, action=InputAction(kind=ActionKind.TYPE, target=_ZONE, value="9"), requests=()),
        f.frame(
            2,
            action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
            requests=(
                f.request(
                    method="POST", url=URL, request_body=f.body('{"workArea": "ONE", "zone": 9}')
                ),
            ),
        ),
    )
    without = (
        f.frame(
            0, action=InputAction(kind=ActionKind.TYPE, target=_WORK_AREA, value="TWO"), requests=()
        ),
        f.frame(
            1,
            action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
            requests=(
                f.request(method="POST", url=URL, request_body=f.body('{"workArea": "TWO"}')),
            ),
        ),
    )

    with pytest.raises(InductionFailed, match="not two runs of one task"):
        align(filled, without)


def test_a_value_matching_two_writes_is_bound_to_neither() -> None:
    """The ambiguity rule applies across a frame's writes, not just within
    one body -- a value cannot say which write it belongs to any more than
    it can say which key."""
    typing = f.frame(0, action=InputAction(kind=ActionKind.TYPE, target=f.fingerprint(), value="1"))
    saving = f.frame(
        1,
        requests=(
            f.request(request_id="req-1", request_body=f.body('{"voiceCode": 1}')),
            f.request(
                request_id="req-2",
                url="https://wms.test/api/other",
                request_body=f.body('{"priority": 1}'),
            ),
        ),
    )

    assert binding.key_filled_by(typing, saving) is None


_VOICE_CODE = f.fingerprint(node_id="voice-code", accessible_name="Voice Code")
_ABSOLUTE = f.fingerprint(node_id="absolute", accessible_name="Absolute Priority")
_HOME = f.fingerprint(node_id="home", accessible_name="Home Work Area Absolute Priority")
_DESCRIPTION = f.fingerprint(node_id="description", accessible_name="Description")


def test_a_step_conditional_on_a_parameter_nobody_declared_is_refused() -> None:
    """`when` names a parameter the same way a template does, and the same
    check catches it: a step conditional on something nobody can supply is a
    step that never happens, and nothing would say why."""
    with pytest.raises(InvariantViolation, match="references undeclared parameters: whichever"):
        f.skill_version(steps=(f.step(when="whichever"),), parameters=(f.parameter(),))


def test_two_fields_nobody_filled_are_two_parameters_with_two_absent_forms() -> None:
    """Grouping asks whether two sites hold one value, and an absence is not a
    value: a number the form nulls and a text box it empties both tidy to `""`,
    so two unrelated optional fields merged into one parameter carrying
    whichever absent form came first. The other field then got that form sent
    to it on every run -- `null` into a text box, and unquoted, because the
    unquoting follows the parameter's name to every site sharing it.

    Proved on the rendered body: each field keeps its own absent form, and
    both halves of the template are valid JSON supplied or omitted."""
    filled = {"deltaPriority": 1, "distanceThreshold": "1"}
    skipped = {"deltaPriority": None, "distanceThreshold": ""}

    parameterisation = parameterise(_run(filled), _run(skipped))

    absent_forms = {p.name: p.absent_as for p in parameterisation.parameters}
    assert absent_forms == {"delta_priority": "null", "distance_threshold": '""'}

    template = Template(
        substitute_body(
            json.dumps(filled),
            parameterisation.for_step(0),
            unquoted=parameterisation.unquoted_sites(0),
        )
    )
    supplied = json.loads(template.render({"delta_priority": "4", "distance_threshold": "7"}))
    assert supplied == {"deltaPriority": 4, "distanceThreshold": "7"}
    omitted = json.loads(template.render({"delta_priority": "null", "distance_threshold": ""}))
    assert omitted == {"deltaPriority": None, "distanceThreshold": ""}


def test_two_optional_fields_that_shared_a_value_are_still_two_parameters() -> None:
    """The absent form keeps two *skipped* fields apart. It says nothing about
    two *filled* ones: both these fields carry 1 in the run that filled them and
    null in the run that did not, so the whole key matched and they collapsed
    into one parameter with two sites. Supplying 7 then wrote 7 to both --
    and made both gestures conditional on `delta_priority`, so the UI path
    typed it into both boxes too.

    Two body keys really can hold one value -- Blue Yonder's adjust payload
    sends the detail number as both `lpn` and `detailNumber` -- but what proves
    that is both runs agreeing at both keys with two different values. An
    optional field agrees once, against an absence, and every absence looks
    alike."""
    filled = {"deltaPriority": 1, "distanceThreshold": 1}
    skipped = {"deltaPriority": None, "distanceThreshold": None}

    parameterisation = parameterise(_run(filled), _run(skipped))

    assert {(sub.site, sub.parameter) for sub in parameterisation.substitutions[0]} == {
        (JsonBodySite("/deltaPriority"), "delta_priority"),
        (JsonBodySite("/distanceThreshold"), "distance_threshold"),
    }
    template = Template(
        substitute_body(
            json.dumps(filled),
            parameterisation.for_step(0),
            unquoted=parameterisation.unquoted_sites(0),
        )
    )
    one_of_them = json.loads(template.render({"delta_priority": "7", "distance_threshold": "null"}))
    assert one_of_them == {"deltaPriority": 7, "distanceThreshold": None}


def test_two_body_fields_the_runs_wrote_differently_are_two_parameters() -> None:
    """Tidying joins a keystroke to the body site it filled, and that is all it
    is for. Between two body sites there is no keystroke and nothing to see
    through -- both texts are what the system stored -- and case-folding them
    merged fields the demonstrations proved differ: every run wrote the slug
    lowercased beside an uppercased work area, and one parameter meant the
    skill sent `NEWAREA` as the slug."""
    parameterisation = parameterise(
        _run({"workArea": "TWOTEST", "slug": "twotest"}),
        _run({"workArea": "THREETE", "slug": "threete"}),
    )

    assert {(sub.site, sub.parameter) for sub in parameterisation.substitutions[0]} == {
        (JsonBodySite("/workArea"), "work_area"),
        (JsonBodySite("/slug"), "slug"),
    }


def test_one_optional_field_sent_in_two_places_is_still_one_parameter() -> None:
    """A form that puts Delta Priority in the query string as well as the body
    sends it in two kinds of site, and only the body leaf carries an absent
    form -- a query string has no way to spell `null`.

    Keyed on the site, the two split: the URL half became a second parameter
    with no absent form, so `_check_runnable` demanded a value for a field the
    other half calls optional, and supplying 7 sent `?deltaPriority=7` beside a
    body still carrying `"deltaPriority":null` -- a silent wrong write."""
    request_a = f.request(
        method="POST",
        url=f"{URL}?deltaPriority=1",
        request_body=f.body(json.dumps({"deltaPriority": 1})),
    )
    request_b = f.request(
        method="POST",
        url=f"{URL}?deltaPriority=",
        request_body=f.body(json.dumps({"deltaPriority": None})),
    )

    parameterisation = parameterise(
        (f.frame(0, requests=(request_a,)),), (f.frame(0, requests=(request_b,)),)
    )

    assert [(p.name, p.optional, p.absent_as) for p in parameterisation.parameters] == [
        ("delta_priority", True, "null")
    ]
    assert {(sub.site, sub.parameter) for sub in parameterisation.substitutions[0]} == {
        (JsonBodySite("/deltaPriority"), "delta_priority"),
        (UrlQuerySite("deltaPriority"), "delta_priority"),
    }
    assert parameterisation.unquoted_sites(0) == frozenset({JsonBodySite("/deltaPriority")}), (
        "the body leaf loses its quotes so it can render `null`; the URL is text either way"
    )


def test_two_different_fields_that_shared_a_value_are_not_rejoined() -> None:
    """The rejoin above asks whether two sites carried the same two values. That
    is not enough on its own: a query parameter and a body leaf can agree on
    both values and still name two different fields, and the run that skipped
    the body field empties the query string for its own reason.

    Welded, one `distance_threshold` filled both sites -- supplying 7 sent
    `?deltaPriority=7` as well, a value written to a field nobody supplied. Two
    parameters is the answer, even though the URL half then comes out required
    for a field the body half calls optional: one extra prompt beats a wrong
    write."""
    request_a = f.request(
        method="POST",
        url=f"{URL}?deltaPriority=1",
        request_body=f.body(json.dumps({"distanceThreshold": 1})),
    )
    request_b = f.request(
        method="POST",
        url=f"{URL}?deltaPriority=",
        request_body=f.body(json.dumps({"distanceThreshold": None})),
    )

    parameterisation = parameterise(
        (f.frame(0, requests=(request_a,)),), (f.frame(0, requests=(request_b,)),)
    )

    assert {(sub.site, sub.parameter) for sub in parameterisation.substitutions[0]} == {
        (JsonBodySite("/distanceThreshold"), "distance_threshold"),
        (UrlQuerySite("deltaPriority"), "delta_priority"),
    }


def test_substitute_body_unquotes_only_the_parameter_named_for_it() -> None:
    """`json.dumps` quotes every placeholder alike; `unquoted` says which ones
    lose those quotes afterwards -- the fields whose absent form is not itself
    a JSON string. Proved on the rendered text, parsed as JSON: a supplied
    value comes back a JSON number for the named field either way, but the
    absent form comes back a JSON `null` only for the field named in
    `unquoted` -- for the other it is still the four characters `"null"`."""
    body = json.dumps({"workArea": "TWOTEST", "deltaPriority": 1, "voiceCode": 1})
    replacements = {
        JsonBodySite("/deltaPriority"): "${delta_priority}",
        JsonBodySite("/voiceCode"): "${voice_code}",
    }

    rendered = substitute_body(
        body, replacements, unquoted=frozenset({JsonBodySite("/deltaPriority")})
    )
    template = Template(rendered)

    filled = json.loads(template.render({"delta_priority": "4", "voice_code": "9"}))
    assert filled["deltaPriority"] == 4, "unquoted: a JSON number"
    assert filled["voiceCode"] == "9", "left quoted: still a JSON string"

    absent = json.loads(template.render({"delta_priority": "null", "voice_code": "null"}))
    assert absent["deltaPriority"] is None, "unquoted: the demonstration's own JSON null"
    assert absent["voiceCode"] == "null", "left quoted: still a JSON string"


def test_a_number_field_the_form_empties_keeps_its_quotes() -> None:
    """The mirror, and the reason the quotes cannot be decided from the filled
    type either: this form empties its number box to `""` rather than nulling
    it. Unquoted on the strength of the `1`, the slot renders `{"qty":}` on
    every run that leaves the field out -- which is not JSON."""
    parameterisation = parameterise(
        _run({"workArea": "TWOTEST", "qty": 1}), _run({"workArea": "TWOTEST", "qty": ""})
    )

    qty = next(p for p in parameterisation.parameters if p.name == "qty")
    assert qty.absent_as == '""'
    assert qty.unquoted_as is None, 'a quoted slot: `""` is what it has to render'
    template = Template(
        substitute_body(
            json.dumps({"workArea": "TWOTEST", "qty": 1}),
            parameterisation.for_step(0),
            unquoted=parameterisation.unquoted_sites(0),
        )
    )
    assert json.loads(template.render({"work_area": "TWOTEST", "qty": ""}))["qty"] == ""


def _note_version() -> SkillVersion:
    """The version the test above induces, written out: `note` unquoted so its
    absence can be a JSON null, and text so a supplied value is text."""
    return f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    url=Template(URL),
                    body=Template('{"workArea":"${work_area}","note":${note}}'),
                    headers=(
                        HeaderPlan(
                            name="cookie",
                            sensitivity=Sensitivity.SESSION,
                            credential_ref=_COOKIE_REF,
                        ),
                    ),
                ),
            ),
        ),
        parameters=(
            f.parameter(name="work_area", observed_values=("ONE", "TWO")),
            f.parameter(
                name="note",
                absent_as="null",
                unquoted_as="string",
                observed_values=("check dock 4",),
            ),
        ),
    )


async def _sent(parameters: dict[str, str], version: SkillVersion) -> dict[str, object]:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, version, PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"), parameters=parameters, authorized_by="supervisor"
        ),
    )

    assert len(http.sent) == 1
    body = http.sent[0]["body"]
    assert isinstance(body, str)
    return dict(json.loads(body))


async def test_a_value_supplied_for_an_unquoted_text_field_arrives_as_text() -> None:
    """The slot holds JSON, so the value goes in as the JSON of the type the
    demonstration filled it with -- read off what actually left the process.
    Pasted in raw it is `{"note":check dock 9}`, which no warehouse parses."""
    assert await _sent({"work_area": "NEWAREA", "note": "check dock 9"}, _note_version()) == {
        "workArea": "NEWAREA",
        "note": "check dock 9",
    }


async def test_an_unquoted_text_field_nobody_supplied_still_sends_the_null() -> None:
    """And the reason its slot is unquoted in the first place: the run that
    skipped this field sent a real JSON `null`, not the four characters."""
    sent = await _sent({"work_area": "NEWAREA"}, _note_version())
    assert sent["note"] is None, "a real JSON null, not the string 'null'"


def test_an_optional_parameter_nobody_supplied_still_runs_but_a_required_one_does_not() -> None:
    """A field one demonstration skipped is optional, and a run that leaves it
    out the same way is not a run missing something -- `_check_runnable` must
    let it through rather than demanding a value nobody who performed the
    task supplied either. The field every demonstration filled stays
    required, though: nothing has shown the task works without it, so a
    version asking for that and getting nothing is still refused, with the
    message this always raised."""
    request = ExecutionRequest(skill_id=SkillId("skill-1"), parameters={})

    optional = f.skill_version(
        stage=PromotionStage.SHADOW,
        parameters=(f.parameter(absent_as="null"),),
    )
    _check_runnable(optional, request)  # does not raise

    required = f.skill_version(stage=PromotionStage.SHADOW, parameters=(f.parameter(),))
    with pytest.raises(NotRunnable, match="no value supplied for shipment_id"):
        _check_runnable(required, request)


def test_substitute_body_does_not_unquote_a_field_that_only_looks_like_the_marker() -> None:
    """The quote-stripping targets the one leaf the parameter actually
    substituted into, not every occurrence of its placeholder text in the
    document. An operator who happened to type the literal string
    "${delta_priority}" into some unrelated field must not have that field's
    quotes stripped out from under it -- that would leave the body invalid
    JSON over a value nobody named as a parameter at all."""
    body = json.dumps({"workArea": "TWOTEST", "deltaPriority": 1, "note": "${delta_priority}"})
    replacements = {JsonBodySite("/deltaPriority"): "${delta_priority}"}

    rendered = substitute_body(
        body, replacements, unquoted=frozenset({JsonBodySite("/deltaPriority")})
    )

    assert rendered == (
        '{"workArea":"TWOTEST","deltaPriority":${delta_priority},"note":"${delta_priority}"}'
    )


def test_a_field_that_may_be_left_out_and_one_that_may_not_cannot_disagree() -> None:
    """Optional means "a run may leave this out", and `absent_as` is the only
    thing that says what goes on the wire when one does -- so they were never
    two facts. Stored as two, they could contradict each other, and the two
    sides of the system asked different questions: emission unquoted the slot
    on the strength of the absent form, execution declined to fill it on the
    strength of the flag, and the write went out as `{"deltaPriority":}`.

    Now the one derives from the other, and the contradiction cannot be
    written down at all -- not by a fixture, an editing API or a migration."""
    assert f.parameter(absent_as="null").optional is True
    assert f.parameter().optional is False, "nothing has shown the task works without it"

    with pytest.raises(TypeError):
        f.parameter(absent_as="null", optional=False)


def test_a_parameter_refuses_an_absent_as_that_is_not_json() -> None:
    """`absent_as` is read back later as JSON without a guard of its own --
    `_perform` trusts it because nothing else can construct a `Parameter`
    without going through this check first. A value that is not valid JSON
    -- a fixture, an editing API, a migration, never induction itself, which
    always writes it with `json.dumps` -- must be refused here, where the
    message names what is wrong, rather than surfacing as a JSONDecodeError
    stack trace mid-run."""
    with pytest.raises(InvariantViolation, match="not valid JSON"):
        f.parameter(absent_as="not json")


# Everything below drives a whole run through `ExecuteSkill` and reads what
# actually left the process, rather than the pieces that build up to it.
# `deltaPriority` is unquoted in the body template the way `substitute_body`
# really leaves a numeric field, so its absent form on the wire is a JSON
# `null` and not the four characters `"null"`.

_COOKIE_REF = "blue_yonder/SG/cookie"
_SCOPED = f"{f.TENANT}/{_COOKIE_REF}"


def _work_area_write_step() -> SkillStep:
    return f.step(
        index=0,
        network_plan=f.network_plan(
            url=Template("https://wms.test/data/WM/wm/workareas"),
            body=Template('{"workArea":"${work_area}","deltaPriority":${delta_priority}}'),
            headers=(
                HeaderPlan(
                    name="cookie", sensitivity=Sensitivity.SESSION, credential_ref=_COOKIE_REF
                ),
                HeaderPlan(name="Referer", sensitivity=Sensitivity.TRANSPORT, managed=True),
                HeaderPlan(
                    name="Content-Type",
                    sensitivity=Sensitivity.SEMANTIC,
                    value=Template("application/json"),
                ),
            ),
        ),
    )


def _work_area_version() -> SkillVersion:
    return f.skill_version(
        steps=(_work_area_write_step(),),
        parameters=(
            f.parameter(name="work_area", observed_values=("ONE", "TWO")),
            f.parameter(
                name="delta_priority",
                absent_as="null",
                unquoted_as="number",
                observed_values=("1",),
            ),
        ),
    )


async def _promoted(uow: FakeUnitOfWork, version: SkillVersion, stage: PromotionStage) -> None:
    """A skill at ``stage``, promoted one rung at a time as a reviewer would."""
    skill = f.skill(versions=0)
    skill.add_version(version)
    current = PromotionStage.RECORDED
    while current is not stage:
        current = current.next_stage()
        version.promote(current, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


async def test_a_run_that_supplies_no_value_for_an_optional_parameter_sends_the_absent_form() -> (
    None
):
    """The demonstration that skipped Delta Priority sent a real JSON `null`
    for it, not the string `"null"` -- and a run that leaves the same field
    out has to put the same thing on the wire, read from what the fake HTTP
    caller actually recorded rather than from the template that built it."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"work_area": "TWO"},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    sent_body = http.sent[0]["body"]
    assert isinstance(sent_body, str)
    body = json.loads(sent_body)
    assert body["deltaPriority"] is None, "a real JSON null, not the string 'null'"


async def test_a_run_that_supplies_the_value_sends_the_value() -> None:
    """The same field, filled: nothing about the absent-form machinery should
    get in the way of an ordinary run that supplies every parameter."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"work_area": "ONE", "delta_priority": "1"},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    sent_body = http.sent[0]["body"]
    assert isinstance(sent_body, str)
    body = json.loads(sent_body)
    assert body["deltaPriority"] == 1


async def test_an_empty_value_supplied_for_an_optional_parameter_is_nobody_supplying_it() -> None:
    """A form is the only place these values come from, and a form hands back
    `""` for the box nobody typed in -- so an empty supplied value is the same
    run as an omitted one, and the two mediums have to read it the same way.

    `_perform_in_ui` already does: it skips the conditional step. The network
    path tested for the key's presence instead, so the same run sent the empty
    verbatim -- into a field unquoted in the template, which renders
    `{"deltaPriority":}` and is not JSON at all."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"work_area": "TWO", "delta_priority": ""},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    sent_body = http.sent[0]["body"]
    assert isinstance(sent_body, str)
    body = json.loads(sent_body)
    assert body["deltaPriority"] is None, "the absent form, the same as omitting it entirely"


async def test_a_quantity_that_would_write_a_field_nobody_demonstrated_is_refused() -> None:
    """An unquoted slot takes whatever it is given as JSON, so a supplied
    value is not only a value: `2,"approved":true` in Delta Priority renders a
    valid body carrying a key no demonstration ever sent, and a warehouse has
    no way to know the difference. Refused before the run starts -- a job
    whose fourth step is the poisoned one has already written three times by
    the time rendering sees it."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    with pytest.raises(NotRunnable, match="delta_priority is sent as a bare number"):
        await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"work_area": "PACK-3", "delta_priority": '2,"approved":true'},
                authorized_by="supervisor",
            ),
        )

    assert http.sent == [], "a refusal must not send anything"


async def test_a_value_that_would_end_its_own_string_is_escaped_rather_than_refused() -> None:
    """The milder half of the same hole, and it closes by encoding rather than
    by refusing. A quoted body slot is text inside a JSON string, exactly like
    the unquoted string slot beside it, so the value is `json.dumps`-escaped on
    its way in: the `"` it carries becomes `\\"` and writes nothing but its own
    field. Refusing instead cost every legitimate value with a quote in it --
    a search term, an address line, and every XML body there has ever been."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"work_area": 'PACK-3","deltaPriority":9', "delta_priority": "1"},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    sent_body = http.sent[0]["body"]
    assert isinstance(sent_body, str)
    body = json.loads(sent_body)
    assert body == {"workArea": 'PACK-3","deltaPriority":9', "deltaPriority": 1}, (
        "the whole value in its own field, and the field beside it untouched"
    )


async def test_a_supplied_value_never_adds_a_field_the_demonstration_did_not_send() -> None:
    """The rule the encoding has to keep: whatever a value carries, the body
    that goes out has exactly the keys the demonstration sent. Asserted on the
    keys rather than on the text, because "it did not break out" is the claim
    and a rendered string only looks like it."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    for value in ('","approved":true,"x":"', "back\\slash", '""', 'he said "go"'):
        await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"work_area": value, "delta_priority": "1"},
                authorized_by="supervisor",
            ),
        )
        sent_body = http.sent[-1]["body"]
        assert isinstance(sent_body, str)
        body = json.loads(sent_body)
        assert list(body) == ["workArea", "deltaPriority"], f"{value!r} wrote a key of its own"
        assert body["workArea"] == value


def test_the_absent_form_of_a_text_field_is_the_empty_string_not_two_quotes() -> None:
    """`rejects` waves through the form the demonstration itself sent, because
    execution puts it there when nobody supplies a value. But what execution
    puts there is what the slot can hold, and a slot that keeps its quotes
    holds the empty string -- not the two characters `absent_as` stores.

    Compared against the stored JSON instead, a supplied `""` was read as
    "leaving it out" and substituted as text into a slot that already had
    quotes round it, and the write went out with four in a row. Leaving it out
    is what an empty value already means, on both paths -- and the two
    characters are now an ordinary value, escaped into the slot like any
    other, which is the second half of why four quotes cannot happen."""
    note = Parameter(name="note", kind=ParameterKind.INPUT, absent_as='""')

    assert note.absent_value == ""
    assert note.rejects("") is None, "an empty value is nobody supplying one"
    assert note.rejects('""') is None, "an ordinary value now; the slot escapes it"


def test_a_control_character_is_refused_wherever_the_value_is_not_the_body() -> None:
    """The one character-level refusal left. A value is substituted as text
    into headers and URLs as well as bodies -- a `\\r` there ends the header
    value and starts a second header -- and nothing on a parameter separates
    the body leaf from the header. A whole body is the exception: it is not
    inside anything, and an XML envelope is full of newlines."""
    note = Parameter(name="note", kind=ParameterKind.INPUT)
    envelope = Parameter(name="envelope", kind=ParameterKind.INPUT, is_the_body=True)

    assert note.rejects("check dock 9") is None
    assert note.rejects("one\r\nTwo: three") == (
        "note is substituted as text wherever it is sent, and no URL or header "
        "can carry the '\\r' in 'one\\r\\nTwo: three'"
    )
    assert envelope.rejects("<a>\n  <b>x</b>\n</a>") is None


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_a_number_json_cannot_spell_is_not_a_number(value: str) -> None:
    """A bare slot renders what it is given verbatim, and `json.loads` reads
    these three because Python writes them. JSON has no such literals: the
    write goes out as `{"deltaPriority":NaN}`, which a WMS that parses
    strictly refuses whole and one that does not stores unreadably."""
    delta = Parameter(
        name="delta_priority", kind=ParameterKind.INPUT, absent_as="null", unquoted_as="number"
    )

    assert delta.rejects(value) == (
        f"delta_priority is sent as a bare number and {value!r} is not one"
    )


async def test_a_value_a_response_produced_is_escaped_into_the_body() -> None:
    """The other half of the same path. A derived value that a quoted slot can
    hold once it is encoded is sent, not refused: the answer said `he said
    "go"` and that is what goes into the note, whole, with the body still one
    field wide."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    http.answer(status_code=200, text=json.dumps({"note": 'he said "go"'}))
    http.answer(status_code=200, text="{}")

    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(method="GET", url=Template(URL), body=None),
            ),
            f.step(
                index=1,
                network_plan=f.network_plan(url=Template(URL), body=Template('{"note":"${note}"}')),
            ),
        ),
        parameters=(
            Parameter(
                name="note",
                kind=ParameterKind.DERIVED,
                source_step_index=0,
                source_pointer="/note",
            ),
        ),
    )
    await _promoted(uow, version, PromotionStage.ASSISTED)

    run = await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(skill_id=SkillId("skill-1"), parameters={}, authorized_by="supervisor"),
    )

    assert run.status is RunStatus.SUCCEEDED
    sent_body = http.sent[1]["body"]
    assert isinstance(sent_body, str)
    assert json.loads(sent_body) == {"note": 'he said "go"'}


async def test_a_body_that_is_one_parameter_is_sent_exactly_as_supplied() -> None:
    """A body that is not JSON -- SOAP here -- is parameterised whole: the
    template is the placeholder and nothing else. Such a value *is* the body,
    so it is neither escaped nor refused for what it carries. Both were wrong
    and one was fatal: an XML envelope carries a `"` on every single run, so
    the quoted-slot refusal made this task permanently unrunnable."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")

    envelope = (
        '<?xml version="1.0"?>\n'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">\n'
        "  <soap:Body><Release id=\"W-42\" note='he said &quot;go&quot;'/></soap:Body>\n"
        "</soap:Envelope>"
    )
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(url=Template(URL), body=Template("${envelope}")),
            ),
        ),
        parameters=(Parameter(name="envelope", kind=ParameterKind.INPUT, is_the_body=True),),
    )
    await _promoted(uow, version, PromotionStage.ASSISTED)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"envelope": envelope},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    assert http.sent[0]["body"] == envelope, "byte for byte; there is nothing round it"


async def test_a_required_input_nobody_supplied_still_refuses_to_run() -> None:
    """`work_area` is filled in every demonstration there is, so it stays
    required even though `delta_priority` sits right beside it as optional --
    a run that supplies neither still fails for the field that has no absent
    form of its own, with the message this always raised."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    with pytest.raises(NotRunnable, match="no value supplied for work_area"):
        await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"), parameters={}, authorized_by="supervisor"
            ),
        )

    assert http.sent == [], "a refusal must not send anything"


# On a system with no writable API, the form is the only way in -- so the
# absent-form rule above has to hold on the gesture path too, or a run that
# clicks types into a field nobody gave it a value for. Two keystrokes, one
# conditional on ``delta_priority``: whether the driver was asked for the
# second one is the whole test.

_WORK_AREA_FIELD = f.fingerprint(node_id="work-area-field", accessible_name="Work Area")
_DELTA_PRIORITY_FIELD = f.fingerprint(
    node_id="delta-priority-field", accessible_name="Delta Priority"
)


def _typed_ui_step(index: int, *, when: str | None, target: object, parameter: str) -> SkillStep:
    return f.step(
        index=index,
        when=when,
        network_plan=None,
        ui_plan=UiPlan(
            action=ActionKind.TYPE,
            target=target,
            value=Template(f"${{{parameter}}}"),
            locators=(
                ControlLocator(strategy=LocatorStrategy.COMPONENT, query=Template(f"#{parameter}")),
            ),
        ),
    )


def _version_with_optional_delta() -> SkillVersion:
    return f.skill_version(
        steps=(
            _typed_ui_step(0, when=None, target=_WORK_AREA_FIELD, parameter="work_area"),
            _typed_ui_step(
                1, when="delta_priority", target=_DELTA_PRIORITY_FIELD, parameter="delta_priority"
            ),
        ),
        parameters=(
            f.parameter(name="work_area", observed_values=("ONE", "TWO")),
            f.parameter(name="delta_priority", absent_as="null", observed_values=("1",)),
        ),
    )


async def _run_by_clicking(values: dict[str, str], *, ui: FakeUiDriver) -> Run:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _promoted(uow, _version_with_optional_delta(), PromotionStage.ASSISTED)

    return await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory(), ui).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters=values,
            authorized_by="supervisor",
            medium=Medium.UI,
        ),
    )


async def test_a_conditional_step_with_no_value_is_not_typed() -> None:
    """On a system with no writable API, the form is the only way in -- so the
    skip has to work here, not only on the call.

    Sent as `""`, not simply left out of the request: a template that still
    names `${delta_priority}` renders an omitted key into a `KeyError` on its
    own, which would fail this step for an unrelated reason and prove nothing
    about the guard under test. An empty string is the one shape that reaches
    `ui.perform` unless something stops it on purpose -- the same shape a
    console forwards for a field a person left blank."""
    driver = FakeUiDriver()

    await _run_by_clicking({"work_area": "PACK-3", "delta_priority": ""}, ui=driver)

    typed = [asked for asked in driver.asked if asked["action"] is ActionKind.TYPE]
    assert [asked["value"] for asked in typed] == ["PACK-3"], "the skipped field was typed anyway"


async def test_a_conditional_step_with_a_value_is_typed() -> None:
    """The mirror of the case above: a value somebody did supply is the one
    thing the guard must never withhold from the control it belongs to."""
    driver = FakeUiDriver()

    await _run_by_clicking({"work_area": "PACK-3", "delta_priority": "4"}, ui=driver)

    typed = [asked for asked in driver.asked if asked["action"] is ActionKind.TYPE]
    assert [asked["value"] for asked in typed] == ["PACK-3", "4"]


async def test_a_conditional_step_with_the_parameter_absent_is_skipped_not_failed() -> None:
    """`driver.asked` cannot tell this case apart from the one above: with the
    key left out of `values` entirely, `plan.value.render` would raise
    `KeyError` on its own before ever reaching `ui.perform`, the same as it
    would without the guard. What only the guard decides is which disposition
    that step gets -- and the difference is not cosmetic. `SKIPPED` folds into
    `Verdict.WITHHELD` and lets the run succeed; a step that instead fails
    degrades the run and blocks the skill's climb up the promotion ladder, for
    a parameter no demonstration required either."""
    driver = FakeUiDriver()

    run = await _run_by_clicking({"work_area": "PACK-3"}, ui=driver)

    assert run.steps[1].disposition is StepDisposition.SKIPPED
    assert run.status is RunStatus.SUCCEEDED


# --- The evidence itself -----------------------------------------------------
#
# Everything above this line is unit-scale. Below it, the two work areas a
# person created by hand in a real Blue Yonder WMS on 2026-08-27 -- captured
# passively, trimmed to the two doings, hostname swapped for wms.acme.test --
# go through the whole passive path: batches, candidate, two recordings, real
# induction. This is the pair that used to come back "the runs are not two runs
# of one task".

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "work_areas"
WATCHED = datetime(2026, 8, 27, 13, 0, tzinfo=UTC)


class _HealsTheSession:
    """Repairs the one thing the step was missing, the way the real healer
    repairs a session that aged out: it puts the credential back and says so."""

    def __init__(self, vault: FakeCredentialVault) -> None:
        self._vault = vault
        self.asked = 0

    async def attempt(self, ctx: RequestContext, **kwargs: object) -> Healed:
        self.asked += 1
        await self._vault.store(_SCOPED, "session=fresh")
        return Healed(
            remedy=Remedy.REFRESH_SESSION, because="the session had gone", detail="renewed it"
        )


async def test_a_healed_step_is_retried_with_the_parameters_it_was_performed_with() -> None:
    """The retry after a heal is the same call, so it needs the same facts.

    It was handed `produces=` and not `parameters=`, so the absent-form fill
    loop ran over an empty tuple, `plan.body.render` raised `KeyError` on the
    optional nobody supplied, and the step failed "no value for parameter
    'delta_priority'". A session expiry -- the ordinary thing the healer exists
    for -- became a hard `FAILED` on any skill with an unsupplied optional, and
    a failure counts towards `DEMOTE_AFTER_FAILURES`.
    """
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)
    healer = _HealsTheSession(vault)  # the vault starts empty: no session at all
    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"work_area": "TWO"},
            authorized_by="supervisor",
        ),
    )

    outcome = await ExecuteStep(uow, http, vault, heal=healer).execute(CTX, run_id=run.id, index=0)

    assert healer.asked == 1
    assert outcome.disposition is StepDisposition.PERFORMED, outcome.detail
    assert "then retried" in (outcome.detail or "")
    sent_body = http.sent[0]["body"]
    assert isinstance(sent_body, str)
    assert json.loads(sent_body)["deltaPriority"] is None, "the absent form, on the retry too"


# --- A loop and a conditional step in one skill -------------------------------
#
# The one pair that tells the two index spaces apart. A loop's bounds count raw
# frames; every other index counts aligned steps -- and putting a dropped
# gesture back moves the step space towards the frame space rather than away
# from it, so the loop's bounds must not be moved along with everything else.
# Nothing induced a loop and a conditional step together, so the comment saying
# that was the only thing defending it.

_ORDER = "https://wms.test/api/orders/55"
