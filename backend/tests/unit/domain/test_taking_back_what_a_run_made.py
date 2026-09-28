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

from dataclasses import replace

from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.skill.reversals import addresses, asks_for, identifies, undoes
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


# -- which field the delete addresses a record by ------------------------------


def _deleting(body: str | None, url: str = f"{TYPES}/GDD") -> tuple[Workflow, dict[str, Gesture]]:
    """The undo job, as its evidence records it: one DELETE, with whatever it
    carried."""
    gesture = _gesture("ges-gone", "DELETE", url, 200)
    said = None if body is None else Body(text=body, size_bytes=len(body))
    gesture.requests = [replace(gesture.requests[0], request_body=said)]
    return _job("wfl_delete", "ges-gone"), {"ges-gone": gesture}


def test_the_fields_a_delete_addresses_a_record_by_are_read_off_the_delete() -> None:
    """Not guessed from a name. `customerType` is the singular of
    `customerTypes`, and that reasoning is what `write_plan` refuses at length
    -- this needs none of it: the delete carries the record it is removing, so
    the field is the one whose value is the segment in the path.

    Measured on the deployment 2026-09-19: the pair was found and not one of
    ninety-two runs could offer the button, because each run's `made` carries
    `customerType` and `longDescription` both."""
    job, gestures = _deleting('{"customerType": "GDD", "longDescription": "a type"}')

    assert identifies(job, gestures) == {"customerType"}


def test_a_delete_that_carried_nothing_says_nothing() -> None:
    """Plenty of platforms answer a delete with an empty request. Then this
    knows nothing, and the old rule -- one record named one way -- stands."""
    job, gestures = _deleting(None)

    assert identifies(job, gestures) == frozenset()


def test_every_field_carrying_the_addressed_value_is_a_candidate() -> None:
    """The deployment's own delete carries `GDD` twice, as `customerType` and
    as `resourceId`, and either would address the record. What settles it is
    the create side: `addresses` keeps whichever of them the run recorded
    making."""
    job, gestures = _deleting('{"customerType": "GDD", "resourceId": "GDD"}')

    assert identifies(job, gestures) == {"customerType", "resourceId"}


def test_a_job_that_deletes_nothing_identifies_nothing() -> None:
    made = _job("wfl_make", "ges-made")
    gestures = _store(("ges-made", "POST", TYPES, 201))

    assert identifies(made, gestures) == frozenset()


def test_the_named_field_is_taken_out_of_a_record_that_says_more() -> None:
    """What the deployment's runs actually hold: the two slots the read-back
    confirmed. One of them addresses the record and the other describes it."""
    made = [{"customerType": "GQX", "longDescription": "leaning new SRO type 007"}]

    assert addresses(made, frozenset({"customerType"})) == ("customerType", "GQX")


def test_the_two_sides_narrow_each_other() -> None:
    """The deployment, both halves: the delete addresses `GDD` as either
    `customerType` or `resourceId`, and the create records only the first."""
    made = [{"customerType": "GQX", "longDescription": "type 007"}]

    assert addresses(made, frozenset({"customerType", "resourceId"})) == ("customerType", "GQX")


def test_two_survivors_are_two_names_for_one_record_again() -> None:
    """Refused for the reason this has always refused it: an undo that guesses
    between two names is the one press that removes somebody else's record."""
    made = [{"customerType": "GQX", "resourceId": "R-9"}]

    assert addresses(made, frozenset({"customerType", "resourceId"})) is None


def test_a_named_field_the_record_does_not_carry_addresses_nothing() -> None:
    """The delete says it addresses by `customerType` and this run recorded no
    such field. Nothing to press, rather than the first field that comes to
    hand."""
    assert addresses([{"longDescription": "a type"}], frozenset({"customerType"})) is None


def test_without_a_named_field_the_old_rule_stands() -> None:
    """One record named one way, or nothing. A delete whose evidence does not
    say which field it addresses leaves this exactly as it was."""
    assert addresses([{"customerType": "GQX", "longDescription": "x"}]) is None
    assert addresses([{"customerType": "GQX"}]) == ("customerType", "GQX")


def test_the_undo_is_pressed_in_its_own_vocabulary() -> None:
    """`Delete a Customer Type` declares one parameter and it is called
    `Customer Type` -- the screen's label, which is how every mined job names
    what varies -- while the record it removes is keyed `customerType` in the
    body. A press that sent the body key would name a parameter the job does
    not have, and the run would refuse it as a value nobody supplied."""
    job = replace(_job("wfl_delete", "ges-gone"), parameters=[{"name": "Customer Type"}])

    assert asks_for(job) == "Customer Type"


def test_an_undo_that_varies_two_things_cannot_be_filled_from_one_record() -> None:
    """Which of them wants the id is the wrong kind of guess to make with a
    DELETE."""
    job = replace(
        _job("wfl_delete", "ges-gone"),
        parameters=[{"name": "Customer Type"}, {"name": "Site"}],
    )

    assert asks_for(job) is None


def test_an_undo_that_varies_nothing_is_not_a_press_either() -> None:
    """A delete with no parameter is a delete of whatever it was demonstrated
    on, which is somebody else's record now."""
    assert asks_for(_job("wfl_delete", "ges-gone")) is None


def test_an_undo_whose_one_value_was_mined_twice_still_asks_for_it() -> None:
    """Greyorange, 2026-09-28: Delete a Customer Type was mined with two
    parameters both called Customer Type -- the grid's search filter and a form
    field from an Add opened and abandoned mid-recording. The undo names one
    value, the record's Customer Type, so it asks for that; counting entries
    instead of names left the created SR10 with no Undo at all."""
    undo = replace(
        _job("wfl_delete", "g-delete"),
        parameters=[
            {"key": "filterComboBox", "name": "Customer Type"},
            {"key": "customertype-customerType", "name": "Customer Type"},
        ],
    )

    assert asks_for(undo) == "Customer Type"


def test_an_undo_with_two_different_values_still_asks_for_neither() -> None:
    undo = replace(
        _job("wfl_delete", "g-delete"),
        parameters=[{"name": "Customer Type"}, {"name": "Department"}],
    )

    assert asks_for(undo) is None
