"""What a job would write, said before anybody presses it.

Item 6's other half. The card names the values it holds and what it cannot
take; it does not name the ACT -- and "yes" to a press nobody described is the
gap this closes. Every fact here comes off the step's own recorded call, which
is the same call `http.send` would replay.
"""

from __future__ import annotations

from sro.domain.execution.what_it_writes import what_it_writes
from sro.domain.observation.gesture import Action, Call, Gesture, Target
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.test"
TYPES = f"{WMS}/data/WM/wm/customerTypes"


def _gesture(gesture_id: str, *calls: tuple[str, str, int]) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="str-1",
        batch_id="bat-1",
        at=100.0,
        url=WMS,
        system=WMS,
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=100.0, url=WMS, target=Target(tag="button", name="Save")),
        requests=tuple(
            Call(method=method, url=url, status=status, started_at=100.0)
            for method, url, status in calls
        ),
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="create a customer type",
        narrative="n",
        systems=[WMS],
        steps=[
            Step(order=n, says=f"step {n}", system=WMS, cites=[one]) for n, one in enumerate(cites)
        ],
    )


def test_a_create_names_the_collection_it_posts_to() -> None:
    store = {"ges-0": _gesture("ges-0", ("POST", TYPES, 201))}

    assert what_it_writes(_job("ges-0"), store) == [
        {"does": "create", "record": "customerTypes", "on": WMS, "step": "0"}
    ]


def test_a_delete_names_the_kind_of_record_and_not_the_records_own_id() -> None:
    """`DELETE /customerTypes/GDD` addresses one member of the collection. The
    last segment is what that one record is called, so a card reading it would
    offer to remove a `GDD` -- and `path_shape` leaves it alone, because it
    blanks only a segment carrying a digit."""
    store = {"ges-0": _gesture("ges-0", ("DELETE", f"{TYPES}/GDD", 204))}

    assert what_it_writes(_job("ges-0"), store) == [
        {"does": "remove", "record": "customerTypes", "on": WMS, "step": "0"}
    ]


def test_a_delete_addressing_a_numbered_record_says_the_same_thing() -> None:
    store = {"ges-0": _gesture("ges-0", ("DELETE", f"{TYPES}/4471", 204))}

    assert what_it_writes(_job("ges-0"), store)[0]["record"] == "customerTypes"


def test_a_change_is_a_change_and_never_a_create() -> None:
    store = {"ges-0": _gesture("ges-0", ("PUT", f"{TYPES}/4471", 200))}

    assert what_it_writes(_job("ges-0"), store)[0]["does"] == "change"


def test_a_method_nobody_has_a_word_for_is_left_as_itself() -> None:
    """Inventing a verb is how `PROPFIND` becomes "create"."""
    store = {"ges-0": _gesture("ges-0", ("PROPFIND", TYPES, 207))}

    assert what_it_writes(_job("ges-0"), store)[0]["does"] == "PROPFIND"


def test_a_step_that_only_reads_writes_nothing() -> None:
    store = {"ges-0": _gesture("ges-0", ("GET", TYPES, 200))}

    assert what_it_writes(_job("ges-0"), store) == []


def test_a_step_whose_evidence_has_gone_says_nothing_rather_than_something() -> None:
    assert what_it_writes(_job("ges-missing"), {}) == []


def test_two_writes_are_two_lines_and_never_one() -> None:
    """A job that posts twice makes two records. Saying it once describes half
    of what the press does."""
    store = {
        "ges-0": _gesture("ges-0", ("POST", TYPES, 201)),
        "ges-1": _gesture("ges-1", ("POST", f"{WMS}/data/WM/wm/clients", 201)),
    }

    assert [one["record"] for one in what_it_writes(_job("ges-0", "ges-1"), store)] == [
        "customerTypes",
        "clients",
    ]


def test_the_writes_come_in_step_order() -> None:
    """Read off the steps as a person would do them, whatever order the store
    hands them back in."""
    store = {
        "ges-0": _gesture("ges-0", ("POST", TYPES, 201)),
        "ges-1": _gesture("ges-1", ("DELETE", f"{TYPES}/GDD", 204)),
    }
    job = _job("ges-0", "ges-1")
    job.steps = list(reversed(job.steps))

    assert [one["step"] for one in what_it_writes(job, store)] == ["0", "1"]
