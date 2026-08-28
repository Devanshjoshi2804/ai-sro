"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
    optional_fills,
    parameterise,
)
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InduceSkill, _conditionals
from sro.application.induction.sites import JsonBodySite, substitute_body
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.observation.teach import TeachCandidate
from sro.domain.execution.diagnosis import Remedy
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId, RecordingId, SkillId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import HeaderPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeBlobStore,
    FakeClock,
    FakeCredentialVault,
    FakeEmbedder,
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
    # Not `json.loads`: `deltaPriority`'s absent form is `null`, a JSON number
    # slot, so its placeholder is unquoted here and the raw template is not
    # standalone JSON any more -- only the rendered text is.
    assert saving.network_plan.body.raw == (
        '{"workArea":"${work_area}","deltaPriority":${delta_priority}}'
    )


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


async def test_an_empty_response_leaf_is_not_where_a_skipped_field_comes_from() -> None:
    """The absent form of the optional field -- `""` -- also sat in the earlier
    response, in both runs. `_find_source` requires both runs to match, and
    that requirement is the only thing separating a data path from a
    coincidence; an empty leaf matching an empty value satisfies it for free.

    Read as a dependency, the field becomes DERIVED: filled from a response
    leaf on every run, including the runs an operator wanted blank, with no
    `absent_as` to send instead and no conditional step -- so the keystroke
    `align` excused would come back as nothing at all, and the only evidence of
    how the field is filled by hand is thrown away.
    """
    version = await _induce(
        (
            _looking(0, "3"),
            _typing(1, _DELTA_PRIORITY, "3"),
            _saving(2, {"workArea": "NINE", "deltaPriority": "3"}),
        ),
        (_looking(0, ""), _saving(1, {"workArea": "NINE", "deltaPriority": ""})),
    )

    delta = next(p for p in version.parameters if p.name == "delta_priority")
    assert delta.kind is ParameterKind.INPUT
    assert delta.optional is True
    assert delta.absent_as == '""'
    assert [step.when for step in version.steps if step.when] == ["delta_priority"]


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


async def test_a_field_one_run_cleared_is_one_parameter_on_both_paths() -> None:
    """The mirror of the case above, and the reason the absent form cannot be
    the whole of the grouping key. Both runs touch the control -- one types a
    priority, the other clears it -- so the keystroke is an aligned step rather
    than a dropped one. Only a body leaf ever carries an absent form; a
    keystroke never does. Splitting on that alone tore the typing away from the
    body site it fills: a required `delta_priority` bound to the gesture and an
    optional `delta_priority_2` bound to the write.

    The field would stop being optional on the path an operator actually
    performs it on, and the two mediums would fill it from two different
    answers -- which is the guarantee this branch exists to provide."""
    version = await _induce(
        (_typing(0, _DELTA_PRIORITY, "1"), _saving(1, {"workArea": "ONE", "deltaPriority": 1})),
        (_typing(0, _DELTA_PRIORITY, ""), _saving(1, {"workArea": "ONE", "deltaPriority": None})),
    )

    assert [(p.name, p.optional, p.absent_as) for p in version.parameters] == [
        ("delta_priority", True, "null")
    ]
    typed, wrote = version.steps[0], version.steps[1]
    assert typed.ui_plan is not None and typed.ui_plan.value is not None
    assert typed.ui_plan.value.raw == "${delta_priority}"
    assert wrote.network_plan is not None and wrote.network_plan.body is not None
    assert wrote.network_plan.body.raw == '{"workArea":"ONE","deltaPriority":${delta_priority}}'


def test_a_gesture_align_excused_and_nothing_can_name_refuses_the_pair() -> None:
    """The invariant the case above is one instance of: `align` stops refusing
    an unmatched keystroke only because `optional_fills` promises it comes back
    as a conditional step. A fill that reaches emission with no optional
    parameter to hang on has broken that promise, and the honest answer is the
    refusal `align` would have raised -- not a skill that quietly never fills
    the field again."""
    filled, skipped = _filled("ONE"), _skipped("TWO")
    parameterisation = parameterise(filled, skipped)
    without_optional = replace(
        parameterisation,
        parameters=tuple(replace(p, absent_as=None) for p in parameterisation.parameters),
    )

    with pytest.raises(InductionFailed, match="nothing in the diff calls that field optional"):
        _conditionals(without_optional, optional_fills(filled, skipped))


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


async def test_a_text_field_the_form_nulls_is_a_text_field() -> None:
    """`null` is how this form says "nobody touched it", whatever kind of
    control it is -- so the absent form says nothing about what goes there when
    somebody does type. Read as "not a string, therefore a number", a note
    reading `check dock 9` went into the body raw and the write was not JSON
    at all.

    Which quotes the *slot* has is still the absent form's business: `null`
    cannot be sent from inside a pair of them. What the demonstration filled
    decides what a supplied value has to be -- and here that is text."""
    version = await _induce(
        (
            _typing(0, _WORK_AREA, "TWOTEST"),
            _typing(1, _DELTA_PRIORITY, "check dock 4"),
            _saving(2, {"workArea": "TWOTEST", "note": "check dock 4"}),
        ),
        (
            _typing(0, _WORK_AREA, "THREETE"),
            _saving(1, {"workArea": "THREETE", "note": None}),
        ),
    )

    note = next(p for p in version.parameters if p.name == "note")
    assert note.absent_as == "null", "what the run that skipped it sent"
    assert note.unquoted_as == "string", "what the run that filled it sent"


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


async def test_a_value_that_would_end_its_own_string_is_refused_too() -> None:
    """The milder half of the same hole, and older than the unquoting: a
    quoted slot needs one `"` to get out of, and the body after it is the
    supplier's to write."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    await _promoted(uow, _work_area_version(), PromotionStage.ASSISTED)

    with pytest.raises(NotRunnable, match="work_area is sent inside a quoted string"):
        await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"work_area": 'PACK-3","deltaPriority":9', "delta_priority": "1"},
                authorized_by="supervisor",
            ),
        )

    assert http.sent == []


async def test_a_value_a_response_produced_is_checked_where_it_is_rendered() -> None:
    """Not everything substituted was supplied by whoever asked for the run: a
    derived value comes out of the system's own earlier answer, and the thing
    a loop is acting on comes out of a list. `_check_runnable` never sees
    those, so the same rule is asked again where the body is actually built --
    and the step fails saying why rather than sending a body somebody else's
    quotation marks helped write."""
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

    assert run.status is RunStatus.FAILED
    assert len(http.sent) == 1, "the read went; the write it fed never did"
    assert run.steps[1].detail is not None
    assert "would end it early" in run.steps[1].detail


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
            target=target,  # type: ignore[arg-type]
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


async def _the_two_work_areas(uow: FakeUnitOfWork, blobs: FakeBlobStore) -> TaskCandidate:
    episodes = []
    for index, name in enumerate(("with_a_delta_priority", "without_a_delta_priority")):
        payload = (FIXTURES / f"{name}.ndjson").read_bytes()
        key = f"acme/devansh/2026-08-27/{name}.ndjson"
        blobs.objects[key] = payload
        batch_id = BatchId(f"bat-{name}")
        await uow.observations.add(
            ObservationBatch(
                id=batch_id,
                tenant_id=f.TENANT,
                device_id=DeviceId("dev-1"),
                principal_id=f.OPERATOR,
                mode=CaptureMode.PASSIVE,
                started_at=WATCHED,
                ended_at=WATCHED + timedelta(hours=1),
                received_at=WATCHED + timedelta(hours=1),
                uri=f"s3://sro-artifacts/{key}",
                event_count=len(payload.splitlines()),
                byte_count=len(payload),
            )
        )
        episodes.append(
            Episode(
                started_at=WATCHED + timedelta(minutes=index),
                ended_at=WATCHED + timedelta(hours=1),
                host="wms.acme.test",
                batch_ids=(batch_id,),
                gestures=14,
                calls=3,
            )
        )

    candidate = TaskCandidate(
        id=CandidateId("cnd-work-areas"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST data/WM/wm/workAreas",
        host="wms.acme.test",
        title="Create work areas on wms.acme.test",
        episodes=tuple(episodes),
    )
    await uow.candidates.add(candidate)
    return candidate


async def _induced_from_the_evidence() -> SkillVersion:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _the_two_work_areas(uow, blobs)
    clock = FakeClock(WATCHED + timedelta(days=1))
    induce = InduceSkill(
        uow,
        clock,
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, clock, FakeIdFactory(), FakeEmbedder())),
    )
    taught = await TeachCandidate(
        uow, blobs, clock, FakeIdFactory(), _NeverAsked(), induce
    ).execute(CTX, candidate_id=candidate.id)

    assert taught.skill_id is not None, taught.because
    skill = await uow.skills.get(f.TENANT, taught.skill_id)
    return skill.versions[-1]


class _NeverAsked:
    """A single doing would fall back to a model reading it. Two doings never
    should, and this says so out loud if the diff ever gives up quietly."""

    async def execute(self, ctx: RequestContext, **kwargs: object) -> object:
        raise AssertionError("two doings were diffed by asking a model")


async def test_the_two_work_areas_become_one_skill() -> None:
    """The evidence this whole plan came from: two work areas created by hand
    on 2026-08-27, one with a Delta Priority typed and one with the field left
    alone."""
    version = await _induced_from_the_evidence()

    names = {p.name for p in version.parameters}
    assert {"work_area", "work_area_description"} <= names
    # One parameter per box on the form, and nothing else. The Work Area box
    # uppercases as you type, so `twoTEST` was typed and `TWOTEST` was sent:
    # grouped by exact text those are two parameters, and the second is named
    # after the field's help text -- `work_area_enter_a_unique_name_for_this_
    # large_work_space`, asked of an operator alongside the real one.
    assert names == {
        "work_area",
        "work_area_description",
        "voice_code",
        "absolute_priority",
        "home_work_area_absolute_priority",
        "delta_priority",
    }


async def test_the_only_thing_nobody_has_to_fill_in_is_the_delta_priority() -> None:
    """Every other field was filled in both times, so every other field is
    required. Delta Priority is optional because one of the two doings proves
    the form takes it empty -- and what "empty" means here is the shape the
    evidence actually sent, `null`, not the empty string a different field of
    the same form uses."""
    version = await _induced_from_the_evidence()

    optional = [p for p in version.parameters if p.optional]
    assert [p.name for p in optional] == ["delta_priority"]
    assert optional[0].absent_as == "null"
    # And the gesture only one of the two runs made is kept, conditional on it:
    # this is the only step in either recording that fills that box, so a skill
    # that dropped it could never fill Delta Priority by clicking at all.
    conditional = [step for step in version.steps if step.when]
    assert [step.when for step in conditional] == ["delta_priority"]


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
