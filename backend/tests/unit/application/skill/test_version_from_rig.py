"""A mined workflow as a version the promotion ladder and the runner understand.

Measured over the eight workflows mined from 170 hours of real capture: all
eight build, into 165 steps, every one at RECORDED with `from_one_demonstration`
true -- the strict answer, which is the one this errs towards.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pytest

from sro.application.skill.version_from_rig import parameters_from_rig, version_from_rig
from sro.domain.skill.parameter import Evidence, ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion

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

WORKFLOW = {
    "title": "Create a work activity",
    "narrative": "the operator created a work activity",
    "systems": ["wms.example"],
    "steps": [{"order": 0, "says": "Type the code, then save.", "cites": ["a", "b"]}],
    "parameters": [{"name": "activityCode", "seen_values": ["TEST1", "TEST2"]}],
}
GESTURES = {
    "a": {
        "kind": "type",
        "value": "TEST1",
        "url": "https://wms.example/activities",
        "target": EXTJS,
    },
    "b": {"kind": "click", "url": "https://wms.example/activities", "target": EXTJS},
}

NOW = datetime(2026, 9, 5, tzinfo=UTC)


def _version(
    workflow: Mapping[str, object] = WORKFLOW,
    gestures: Mapping[str, Mapping[str, object]] = GESTURES,
    recordings: Sequence[str] = ("str_1",),
) -> SkillVersion | None:
    return version_from_rig(
        workflow, gestures, recordings=recordings, induced_by="rig", induced_at=NOW
    )


def _built_with_requests() -> SkillVersion:
    """A version built with the network recipe available, which needs a caller
    that knows the system and the facility -- see the module docstring on why
    this module will not guess either."""
    return _built(requests=REQUESTS, target_system="wms.example", facility="SG")


def _built(**kwargs: object) -> SkillVersion:
    """The same, where the test is about what a version SAYS rather than about
    whether one is built at all."""
    version = version_from_rig(
        WORKFLOW,
        GESTURES,
        recordings=("str_1",),
        induced_by="rig",
        induced_at=NOW,
        **kwargs,  # type: ignore[arg-type]
    )
    assert version is not None
    return version


def test_a_mined_workflow_becomes_a_version_nobody_has_reviewed() -> None:
    """RECORDED is the one field that says so, and there is no path here that
    sets anything else. A mined workflow is a proposal about a day of capture;
    nothing in it has been looked at by a person."""
    version = _version()

    assert version is not None
    assert version.stage is PromotionStage.RECORDED
    assert version.promoted_by is None
    assert version.promoted_from == "", "no review happened, so none is named"


def test_one_described_step_over_three_gestures_becomes_three_steps() -> None:
    """A SkillStep performs one thing -- the convention `emit_step` already
    follows -- and a rig step is prose over several gestures. The prose repeats
    across them on purpose: those gestures really were one described step, and
    renaming them apart would invent a distinction the evidence does not make."""
    version = _version()

    assert version is not None
    assert [step.index for step in version.steps] == [0, 1]
    assert {step.intent for step in version.steps} == {"Type the code, then save."}
    assert all(step.ui_plan is not None for step in version.steps)


def test_a_rig_parameter_is_proven_because_two_doings_disagreed() -> None:
    """Stronger footing than the induction path's PROPOSED, and honestly so:
    `parameters_across` reports a control precisely when its value CHANGED
    between occurrences. That is arithmetic over evidence, not a reading."""
    found = parameters_from_rig(WORKFLOW)

    assert [p.name for p in found] == ["activityCode"]
    assert found[0].kind is ParameterKind.INPUT
    assert found[0].evidence is Evidence.PROVEN
    assert found[0].observed_values == ("TEST1", "TEST2")


def test_a_parameter_with_one_value_is_downgraded_rather_than_trusted() -> None:
    """Nothing in the rig produces one. If the store ever holds one, the honest
    reading is that whatever made it did not do the diff PROVEN claims -- so it
    is reported as a reading rather than a fact."""
    odd = {**WORKFLOW, "parameters": [{"name": "activityCode", "seen_values": ["TEST1"]}]}

    assert parameters_from_rig(odd)[0].evidence is Evidence.PROPOSED


def test_without_a_recording_it_refuses_rather_than_minting_one() -> None:
    """Provenance.recording_ids must be non-empty, and the rig has no Recording
    -- its nearest equivalent is the capture stream, which lives in a column
    rather than in the gesture. Minting an id from something to hand would
    satisfy the invariant and lie to `from_one_demonstration`, which decides
    whether a write skill's values were ever diffed."""
    assert _version(recordings=[]) is None


def test_a_workflow_whose_evidence_is_gone_is_not_a_version() -> None:
    """An empty SkillVersion would sit in a library looking runnable. A
    workflow citing gestures this store does not have describes a job nobody
    can perform."""
    assert _version(gestures={}) is None


def test_two_doings_in_one_stream_report_the_strict_answer() -> None:
    """And this is the direction it must err in.

    A job demonstrated twice inside one capture stream is one recording here,
    so a version whose parameters were genuinely proven still reads as
    `from_one_demonstration` -- which makes `values_are_fixed` true and asks
    MORE of it at promotion. Understating the evidence costs a reviewer's time;
    overstating it promotes something on a diff that never happened.
    """
    version = _version()

    assert version is not None
    assert version.from_one_demonstration, "one stream, however many doings"
    assert version.parameters[0].evidence is Evidence.PROVEN, "and the diff still happened"


def test_the_starting_screen_is_claimed_only_for_a_single_recording() -> None:
    """`starts_on` means every demonstration began here. Two that began on
    different screens are saying the screen is not part of the task, and this
    cannot tell which case it is holding."""
    assert _built().starts_on == "https://wms.example/activities"
    two = _version(recordings=["str_1", "str_2"])
    assert two is not None and two.starts_on is None


def test_a_duplicated_recording_id_is_still_one_recording() -> None:
    """`from_one_demonstration` counts the tuple, so a caller passing the same
    stream twice would have doubled the evidence by repeating itself."""
    version = _version(recordings=["str_1", "str_1"])

    assert version is not None
    assert version.from_one_demonstration


@pytest.mark.parametrize("missing", ["title", "narrative", "systems"])
def test_a_workflow_missing_its_prose_is_still_a_version(missing: str) -> None:
    """The prose is for a reviewer; the citations are the mechanism. A model
    that wrote no title has still shown what the operator did."""
    version = _version(workflow={k: v for k, v in WORKFLOW.items() if k != missing})

    assert version is not None and len(version.steps) == 2


REQUESTS = {
    "a": [
        {
            "request_id": "req_1",
            "method": "POST",
            "url": "https://wms.example/data/WM/wm/activities",
            "resource_type": "xhr",
            "started_at": "2026-09-05T10:00:00.000Z",
            "request_headers": {"CSRF-ENCRYPT-TOKEN": "«redacted»"},
            "request_body": {"text": '{"activityCode":"TEST1"}'},
            "status": 201,
        }
    ]
}


def test_a_step_carries_both_recipes_for_the_same_gesture() -> None:
    """ADR 005's dual recipe: the network plan is how a run performs the step
    without a browser, the UI plan is how it performs it when the call no
    longer works. One gesture, so they describe the same act."""
    version = _built_with_requests()

    typed = version.steps[0]
    assert typed.ui_plan is not None and typed.network_plan is not None
    assert typed.network_plan.method == "POST"
    assert typed.network_plan.expected_status == 201


def test_the_parameter_reaches_the_body_as_well_as_the_field() -> None:
    """It was derived from what the operator typed on the screen. That it also
    names a key of the call the screen made is what makes it a skill rather
    than two unrelated readings of one act."""
    version = _built_with_requests()

    assert version.steps[0].placeholders == {"activityCode"}


def test_without_a_facility_no_call_is_planned_rather_than_one_misfiled() -> None:
    """A credential reference is a vault key built from the system and the
    facility. Guessing either would point a run at somebody else's credential,
    so the whole network recipe waits for a caller that knows."""
    version = _built(requests=REQUESTS, target_system="wms.example", facility="")

    assert all(step.network_plan is None for step in version.steps)
    assert version.needs_a_person, "and the gesture ceiling stays where it was"


def test_the_gesture_ceiling_is_the_same_one_every_demonstration_has() -> None:
    """Not a rig defect. `needs_a_person` reads "no network plan and no tool
    plan", and a gesture that caused no call -- typing into a field, where only
    the save posts -- can never have one. Measured on the real corpus: 30 of
    165 steps carry a call. The ceiling lifts through `map_step_to_tool`, the
    same way it does for a skill induced from a recording."""
    version = _built_with_requests()

    assert version.steps[0].network_plan is not None, "the write has a call"
    assert version.steps[1].network_plan is None, "the click that caused none has not"
    assert version.needs_a_person
