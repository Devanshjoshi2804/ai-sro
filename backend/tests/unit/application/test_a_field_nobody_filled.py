"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

import json

import pytest

from sro.application.context import RequestContext
from sro.application.induction import binding, jsonutil
from sro.application.induction.diff import Difference, align, differences, parameterise
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InduceSkill
from sro.application.induction.sites import JsonBodySite
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.skill import SkillVersion
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

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


def _typing(index: int, target: object, value: str) -> object:
    return f.frame(
        index,
        action=InputAction(kind=ActionKind.TYPE, target=target, value=value),  # type: ignore[arg-type]
        requests=(),
    )


def _saving(index: int, body: dict[str, object]) -> object:
    return f.frame(
        index,
        action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
        requests=(f.request(method="POST", url=URL, request_body=f.body(json.dumps(body))),),
    )


def _filled(name: str) -> tuple:
    """The demonstration that typed a Delta Priority."""
    return (
        _typing(0, _WORK_AREA, name),
        _typing(1, _DELTA_PRIORITY, "1"),
        _saving(2, {"workArea": name, "deltaPriority": 1}),
    )


def _skipped(name: str) -> tuple:
    """The demonstration that left it alone, and created the work area anyway."""
    return (_typing(0, _WORK_AREA, name), _saving(1, {"workArea": name, "deltaPriority": None}))


async def _induce(first: tuple, second: tuple) -> SkillVersion:
    uow = FakeUnitOfWork()
    for ident, frames in (("rec-a", first), ("rec-b", second)):
        recording = f.recording(frames=0, id=RecordingId(ident))
        for frame in frames:
            recording.append_frame(frame)
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    await InduceSkill(
        uow,
        FakeClock(),
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())),
    ).execute(CTX, first=RecordingId("rec-a"), second=RecordingId("rec-b"))

    return next(iter(uow.skills.rows.values())).versions[-1]


async def _induce_the_two_work_areas() -> SkillVersion:
    return await _induce(_filled("ONE"), _skipped("TWO"))


async def test_the_step_that_fills_an_optional_field_says_which_one() -> None:
    """Without this, execution has a parameter it may leave out and no idea
    which gesture to leave out with it."""
    version = await _induce_the_two_work_areas()

    optional = [p for p in version.parameters if p.optional]
    assert [p.name for p in optional] == ["delta_priority"]
    conditional = [step for step in version.steps if step.when]
    assert [step.when for step in conditional] == ["delta_priority"]


async def test_the_conditional_step_is_the_gesture_that_fills_the_field() -> None:
    """The point of putting it back. `align` drops this keystroke, and a skill
    without it can only fill Delta Priority by calling the API -- which on the
    system this was taught on does not exist. It has to be clickable, in the
    place the operator did it, sending the value it is conditional on."""
    version = await _induce_the_two_work_areas()

    step = next(s for s in version.steps if s.when == "delta_priority")
    plan = step.ui_plan
    assert plan is not None
    assert plan.action is ActionKind.TYPE
    assert plan.target == _DELTA_PRIORITY
    assert plan.value is not None
    assert plan.value.raw == "${delta_priority}", "it sends what the run was given"
    # In its place: the field is filled before the form is saved, never after.
    saving = next(s for s in version.steps if s.network_plan is not None)
    assert step.index < saving.index
    assert [s.index for s in version.steps] == [0, 1, 2]


async def test_the_field_is_fillable_whichever_run_was_taught_first() -> None:
    """Which recording landed as A is an accident of storage order. Reading
    only run A's dropped gestures would make the field fillable on Tuesday's
    pair and unfillable on Wednesday's."""
    version = await _induce(_skipped("TWO"), _filled("ONE"))

    step = next(s for s in version.steps if s.when == "delta_priority")
    assert step.ui_plan is not None
    assert step.ui_plan.target == _DELTA_PRIORITY


async def test_the_save_that_carries_the_optional_field_is_not_itself_conditional() -> None:
    """The write happens either way -- it sends `null` for the field nobody
    filled. A `when` on it would be a skill that stops creating work areas
    the moment somebody leaves a priority out."""
    version = await _induce_the_two_work_areas()

    saving = next(s for s in version.steps if s.network_plan is not None)
    assert saving.when is None


def test_a_step_conditional_on_a_parameter_nobody_declared_is_refused() -> None:
    """`when` names a parameter the same way a template does, and the same
    check catches it: a step conditional on something nobody can supply is a
    step that never happens, and nothing would say why."""
    with pytest.raises(InvariantViolation, match="references undeclared parameters: whichever"):
        f.skill_version(steps=(f.step(when="whichever"),), parameters=(f.parameter(),))


def _drafting(index: int, target: object, value: str, body: dict[str, object]) -> object:
    """A keystroke that PATCHes a draft as you type it, which is an ordinary
    thing for a form in a single-page application to do."""
    return f.frame(
        index,
        action=InputAction(kind=ActionKind.TYPE, target=target, value=value),  # type: ignore[arg-type]
        requests=(
            f.request(method="PATCH", url=f"{URL}/draft", request_body=f.body(json.dumps(body))),
        ),
    )


async def test_a_conditional_step_replays_no_call_of_its_own() -> None:
    """It is a gesture, and the calls it made are dropped for the reason its
    assertions are: only one run made them, so nothing diffed what they sent
    and every value in them would go out exactly as demonstrated. This PATCH
    carries a work area, and replaying it would write ONE into every later run
    of the skill."""
    version = await _induce(
        (
            _typing(0, _WORK_AREA, "ONE"),
            _drafting(1, _DELTA_PRIORITY, "1", {"workArea": "ONE", "deltaPriority": 1}),
            _saving(2, {"workArea": "ONE", "deltaPriority": 1}),
        ),
        _skipped("TWO"),
    )

    step = next(s for s in version.steps if s.when == "delta_priority")
    assert step.ui_plan is not None, "the field is filled by clicking or not at all"
    assert step.network_plan is None
    # The only call the skill makes is the write both runs sent, which already
    # carries the parameter.
    calls = [s.network_plan for s in version.steps if s.network_plan is not None]
    assert [call.method for call in calls] == ["POST"]


async def test_the_write_still_carries_its_parameters_once_a_step_moves() -> None:
    """Every index the diff produced counts aligned steps, and inserting the
    conditional one moves the save along. Left where it was, the save would be
    handed its neighbour's substitutions -- and send the work area of whoever
    happened to be recorded."""
    version = await _induce_the_two_work_areas()

    saving = next(s for s in version.steps if s.network_plan is not None)
    assert saving.index == 2, "the conditional step took a place before it"
    assert saving.network_plan is not None
    assert saving.network_plan.body is not None
    assert json.loads(saving.network_plan.body.raw) == {
        "workArea": "${work_area}",
        "deltaPriority": "${delta_priority}",
    }


def _looking(index: int, zone: str) -> object:
    return f.frame(
        index,
        action=InputAction(
            kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Find zone")
        ),
        requests=(
            f.request(
                method="GET",
                url="https://wms.test/data/WM/wm/zones",
                request_body=None,
                response_body=f.body(json.dumps({"id": zone})),
            ),
        ),
    )


async def test_a_derived_parameter_still_names_the_step_that_produced_it() -> None:
    """A derived parameter says which step's response carries it, and that
    index counts aligned steps too. Here the operator typed the optional field
    before looking the zone up, so the conditional step lands in front of the
    read -- and an index left where it was would name the keystroke as the
    thing that produced the zone."""
    version = await _induce(
        (
            _typing(0, _DELTA_PRIORITY, "1"),
            _looking(1, "A1"),
            _saving(2, {"workArea": "SEVEN", "deltaPriority": 1, "zoneId": "A1"}),
        ),
        (
            _looking(0, "B2"),
            _saving(1, {"workArea": "SEVEN", "deltaPriority": None, "zoneId": "B2"}),
        ),
    )

    zone = next(p for p in version.parameters if p.name == "zone_id")
    assert zone.source_step_index == 1
    produced_by = version.steps[zone.source_step_index]
    assert produced_by.network_plan is not None
    assert produced_by.network_plan.method == "GET", "it names the read, not the keystroke"
