"""What a job would write, said before anybody presses it.

Item 6's other half. The card names the values it holds and what it cannot
take; it does not name the ACT -- and "yes" to a press nobody described is the
gap this closes. Every fact here comes off the step's own recorded call, which
is the same call `http.send` would replay.
"""

from __future__ import annotations

from sro.domain.execution.what_it_writes import what_it_writes
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.test"
TYPES = f"{WMS}/data/WM/wm/customerTypes"


def _gesture(gesture_id: str, *calls: tuple[str, str, int], names: bool = True) -> Gesture:
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
            Call(
                method=method,
                url=url,
                status=status,
                started_at=100.0,
                response_body=Body(text='{"id": "REC-1"}', size_bytes=15) if names else None,
            )
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


def test_a_page_talking_to_itself_is_not_a_write_anybody_is_warned_about() -> None:
    """Every POST a page makes is not a record. Measured over both tenants'
    evidence, 2026-09-19: Gmail alone made over a hundred of them -- `/log`,
    `/sync/u/0/i/bv`, `batchexecute` -- and the warehouse's own pages fire
    `sessionKeepAlive` and `webPerformanceEntries/batch` from the same click
    that creates a record. Before this rule the card offered to "create a bv
    record on mail.google.com"."""
    chatter = _gesture(
        "ges-0",
        ("POST", "https://mail.google.com/sync/u/0/i/bv", 200),
        ("POST", f"{WMS}/data/WM/wm/webPerformanceEntries/batch", 200),
        names=False,
    )

    assert what_it_writes(_job("ges-0"), {"ges-0": chatter}) == []


def test_a_create_whose_answer_names_nothing_is_still_a_create() -> None:
    """`workOperations` answers 201 and names no record -- five of them in this
    store. A rule that asked every write to name what it made would be silent
    about a job that makes one."""
    quiet = _gesture("ges-0", ("POST", f"{WMS}/data/WM/wm/workOperations", 201), names=False)

    assert what_it_writes(_job("ges-0"), {"ges-0": quiet})[0]["record"] == "workOperations"


def test_a_delete_is_never_asked_to_prove_itself() -> None:
    """The answer to a delete is empty by nature. A rule that made one earn its
    place would be silent about the press a person most needs warning about."""
    gone = _gesture("ges-0", ("DELETE", f"{TYPES}/GDD", 204), names=False)

    assert what_it_writes(_job("ges-0"), {"ges-0": gone}) == [
        {"does": "remove", "record": "customerTypes", "on": WMS, "step": "0"}
    ]


def test_both_writes_of_one_save_are_named() -> None:
    """One logical create is often several physical resources. `new`'s `Create
    a Supplier` PUTs an address and POSTs the supplier from one click, and a
    card built on the single call a replay would send named the address and
    never the supplier."""
    cascade = _gesture(
        "ges-0",
        ("PUT", f"{WMS}/data/WM/wm/addresses/A000010909", 200),
        ("POST", f"{WMS}/data/WM/wm/suppliers", 201),
    )

    assert [one["record"] for one in what_it_writes(_job("ges-0"), {"ges-0": cascade})] == [
        "addresses",
        "suppliers",
    ]


def test_two_demonstrations_of_one_write_are_one_write() -> None:
    """A step cites one gesture per doing. Reading every cited call says a job
    demonstrated three times makes three records."""
    store = {
        "ges-0": _gesture("ges-0", ("POST", TYPES, 201)),
        "ges-1": _gesture("ges-1", ("POST", TYPES, 201)),
    }
    job = _job("ges-0")
    job.steps[0].cites = ["ges-0", "ges-1"]

    assert len(what_it_writes(job, store)) == 1
