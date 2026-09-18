"""Which job undoes another, where a tenant's evidence holds one.

An undo is a job somebody has done, not a call this system invents. The rig
knows what an operator was seen doing and nothing else -- so where the evidence
shows somebody deleting the kind of record a job creates, that deleting is
itself a mined job and can be run, and where it does not there is no undo.

Measured on the real tenant the day this was written: three PUTs to one address
endpoint and not one DELETE anywhere. So this finds nothing there today, on
purpose, and lights up the first time somebody deletes a warehouse equipment
type in front of the recorder.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Call, Gesture, Target
from sro.domain.skill.reversals import addresses, undoes
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.test"
TYPES = f"{WMS}/data/WM/wm/equipmentTypes"


def _gesture(gesture_id: str, method: str, url: str, status: int) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="new",
        stream_id="str-1",
        batch_id="bat-1",
        at=100.0,
        url=WMS,
        system=WMS,
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=100.0, url=WMS, target=Target(tag="button", name="Save")),
        requests=(Call(method=method, url=url, status=status, started_at=100.0),),
    )


def _job(workflow_id: str, cites: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant="new",
        title=workflow_id,
        narrative="n",
        systems=[WMS],
        steps=[Step(order=0, says="s", system=WMS, cites=[cites])],
    )


def _store(*pairs: tuple[str, str, str, int]) -> dict[str, Gesture]:
    return {one[0]: _gesture(*one) for one in pairs}


def test_a_job_that_deletes_what_another_creates_is_its_undo() -> None:
    gestures = _store(
        ("ges-made", "POST", TYPES, 201),
        ("ges-gone", "DELETE", f"{TYPES}/4471", 204),
    )
    creates, deletes = _job("wfl_make", "ges-made"), _job("wfl_delete", "ges-gone")

    assert undoes(creates, gestures, [creates, deletes]) == "wfl_delete"


def test_a_tenant_that_has_never_deleted_one_has_no_undo() -> None:
    """The real store, the day this was written: no DELETE anywhere."""
    gestures = _store(("ges-made", "POST", TYPES, 201))
    creates = _job("wfl_make", "ges-made")

    assert undoes(creates, gestures, [creates]) is None


def test_a_delete_of_something_else_is_not_this_job_s_undo() -> None:
    gestures = _store(
        ("ges-made", "POST", TYPES, 201),
        ("ges-other", "DELETE", f"{WMS}/data/WM/wm/workAreas/9", 204),
    )
    creates, deletes = _job("wfl_make", "ges-made"), _job("wfl_delete", "ges-other")

    assert undoes(creates, gestures, [creates, deletes]) is None


def test_a_job_that_creates_nothing_has_nothing_to_undo() -> None:
    gestures = _store(
        ("ges-read", "GET", TYPES, 200),
        ("ges-gone", "DELETE", f"{TYPES}/4471", 204),
    )
    reads, deletes = _job("wfl_read", "ges-read"), _job("wfl_delete", "ges-gone")

    assert undoes(reads, gestures, [reads, deletes]) is None


def test_an_edit_is_not_an_undo() -> None:
    """A PUT that sets a flag to inactive is how several warehouses retire a
    record, and it is also how every other edit is made. Reading one as an undo
    would offer to take back a job by overwriting the record it made."""
    gestures = _store(
        ("ges-made", "POST", TYPES, 201),
        ("ges-edit", "PUT", f"{TYPES}/4471", 200),
    )
    creates, edits = _job("wfl_make", "ges-made"), _job("wfl_edit", "ges-edit")

    assert undoes(creates, gestures, [creates, edits]) is None


def test_a_job_is_not_its_own_undo() -> None:
    gestures = _store(("ges-made", "POST", TYPES, 201))
    creates = _job("wfl_make", "ges-made")

    assert undoes(creates, gestures, [creates, creates]) is None


def test_an_id_with_no_digit_in_it_is_still_one_record() -> None:
    """The case that kept this dark on the real deployment.

    `path_shape` blanks a segment carrying a DIGIT, which is right for
    `/equipmentTypes/4471` and silent for `/customerTypes/GDD` -- so the id
    survived the blanking, the delete's shape carried the record it happened to
    be demonstrated on, and it could never equal `collection/*`.

    Measured 2026-09-19: this tenant had held `Create a Customer Type` and
    `Delete a Customer Type` for weeks, and this answered None every time.
    """
    gestures = _store(
        ("ges-made", "POST", TYPES, 201),
        ("ges-gone", "DELETE", f"{TYPES}/GDD", 204),
    )

    assert undoes(_job("wfl-made", "ges-made"), gestures, [_job("wfl-gone", "ges-gone")]) == (
        "wfl-gone"
    )


def test_a_delete_two_segments_deeper_is_not_this_undo() -> None:
    """One more segment, which is what deleting a member of a collection is. A
    delete of something inside a member is a different thing entirely."""
    gestures = _store(
        ("ges-made", "POST", TYPES, 201),
        ("ges-gone", "DELETE", f"{TYPES}/GDD/subsites/SG", 204),
    )

    assert undoes(_job("wfl-made", "ges-made"), gestures, [_job("wfl-gone", "ges-gone")]) is None


# -- which record an undo would address ----------------------------------------


def test_one_record_named_one_way_is_what_an_undo_addresses() -> None:
    """The mapping `undo` has said it lacked since it was written. The evidence
    arrived with `made_by`: a step that created something records what the
    warehouse called it."""
    assert addresses([{"customerType": "GGD"}]) == ("customerType", "GGD")


def test_a_run_that_made_two_records_is_offered_no_undo() -> None:
    """It would need two deletes, and an undo that takes back half of what a
    run did is worse than none -- somebody presses it, sees the card go quiet,
    and believes the warehouse is back where it started."""
    assert addresses([{"customerType": "GGD"}, {"customerType": "GKB"}]) is None


def test_a_record_named_two_ways_is_a_record_this_cannot_name() -> None:
    """`made_by` keeps `id`, `code`, `name`, `number` and `key`. A warehouse
    that answered with two of them has not said which one addresses it, and a
    wrong guess removes somebody else's record."""
    assert addresses([{"id": "4471", "code": "GGD"}]) is None


def test_a_run_that_made_nothing_addresses_nothing() -> None:
    assert addresses([]) is None
    assert addresses([{}]) is None


def test_a_name_that_is_only_whitespace_is_not_a_name() -> None:
    assert addresses([{"customerType": "   "}]) is None
