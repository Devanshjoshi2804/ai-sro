"""The undo a rig run has never had.

`reversal.py` answers this for a taught skill. A rig run has no answer at all,
and the panel says so in its own words: *a run the rig drove has neither a
reversal nor anywhere to send "It's wrong", so the card offers neither.* Every
record these runs make is one nobody can take back from the surface they made
it on.

The three facts are `reversal.py`'s, unchanged, because the argument is: a
visible undo is the strongest thing an agentic surface has, and it is where
this design could most easily begin guessing.
"""

from __future__ import annotations

from sro.domain.execution.taking_it_back import takes_back
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.example"
COLLECTION = f"{WMS}/data/WM/wm/customerTypes"


def _doing(gesture_id: str, method: str, url: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=1.0,
        url=f"{WMS}/screen",
        system=WMS,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0, url=f"{WMS}/screen"),
        requests=(Call(method=method, url=url, status=200),),
    )


def _job(workflow_id: str, title: str, says: str, cite: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant="acme",
        title=title,
        narrative="n",
        steps=[Step(order=1, says=says, system=WMS, cites=[cite])],
    )


DELETER = _job("wfl_del", "Delete a Customer Type", "Press Delete.", "g_del")
DELETES = {"g_del": _doing("g_del", "DELETE", f"{COLLECTION}/GDD?siteId=SG&_dc=17894")}


def test_the_job_that_deletes_a_member_of_the_collection_takes_it_back() -> None:
    """The real pair on this deployment: one job POSTs `/customerTypes` and
    another DELETEs `/customerTypes/GDD`."""
    back = takes_back(
        made={"customerType": "GGD"},
        wrote=f"{COLLECTION}?",
        made_by="wfl_create",
        library=[DELETER],
        by_id=DELETES,
    )

    assert back is not None
    assert back.workflow_id == "wfl_del"
    assert back.title == "Delete a Customer Type"
    # In front of somebody BEFORE the press: a press nobody could read is not
    # consent.
    assert back.removes == "Press Delete."
    assert (back.field, back.names) == ("customerType", "GGD")


def test_an_id_with_no_digit_in_it_is_still_an_id() -> None:
    """Not `url_shape`, which blanks a segment carrying a DIGIT -- right for
    `/addresses/A00022791` and wrong here, where the customer types are `GGD`
    and `GDD` and the id survives the blanking."""
    back = takes_back(
        made={"customerType": "GGD"},
        wrote=COLLECTION,
        made_by="wfl_create",
        library=[DELETER],
        by_id=DELETES,
    )

    assert back is not None


def test_a_run_that_read_back_two_identifiers_is_offered_no_undo() -> None:
    """Nothing here can say which names the record, and a delete addressed to a
    guess removes somebody else's."""
    assert (
        takes_back(
            made={"customerType": "GGD", "siteId": "SG"},
            wrote=COLLECTION,
            made_by="wfl_create",
            library=[DELETER],
            by_id=DELETES,
        )
        is None
    )


def test_a_run_that_read_back_nothing_is_offered_no_undo() -> None:
    assert (
        takes_back(
            made={},
            wrote=COLLECTION,
            made_by="wfl_create",
            library=[DELETER],
            by_id=DELETES,
        )
        is None
    )


def test_a_delete_of_another_collection_is_not_this_undo() -> None:
    elsewhere = {"g_del": _doing("g_del", "DELETE", f"{WMS}/data/WM/wm/suppliers/S1")}

    assert (
        takes_back(
            made={"customerType": "GGD"},
            wrote=COLLECTION,
            made_by="wfl_create",
            library=[DELETER],
            by_id=elsewhere,
        )
        is None
    )


def test_a_delete_of_the_collection_itself_is_not_deleting_a_member() -> None:
    """One more segment, which is what deleting a member of a collection IS. A
    delete of the collection is a different and much larger thing."""
    whole = {"g_del": _doing("g_del", "DELETE", COLLECTION)}

    assert (
        takes_back(
            made={"customerType": "GGD"},
            wrote=COLLECTION,
            made_by="wfl_create",
            library=[DELETER],
            by_id=whole,
        )
        is None
    )


def test_a_job_is_never_offered_as_the_undo_of_itself() -> None:
    """A job that deletes what it creates is not an undo of itself."""
    assert (
        takes_back(
            made={"customerType": "GGD"},
            wrote=COLLECTION,
            made_by="wfl_del",
            library=[DELETER],
            by_id=DELETES,
        )
        is None
    )


def test_a_library_that_deletes_nothing_offers_nothing() -> None:
    """Most jobs will have no undo for a long time, because nobody demonstrates
    deleting things. The fallback is the operator fixing it while we watch,
    which is what they were going to do anyway."""
    reads = {"g_del": _doing("g_del", "GET", f"{COLLECTION}/GDD")}

    assert (
        takes_back(
            made={"customerType": "GGD"},
            wrote=COLLECTION,
            made_by="wfl_create",
            library=[DELETER],
            by_id=reads,
        )
        is None
    )
