"""QA 2026-10-02: "is there a warehouse equipment type ZWOYBN" was answered "Yes".

The equipment-types list (88 records) does not hold ZWOYBN. `what_was_found` said
what the read held ("There are 88 equipment types: ...") without ever comparing
it with the value asked about, and a call refused by key was read off the page
and reported as "Read from <target>" -- both of which a model reads as yes.
An existence question is yes only on a record whose value equals the asked one,
no only when the whole list was read, and otherwise "could not tell".
"""

from __future__ import annotations

import json

from sro.application.execution.answer import read_answer
from sro.application.lookup.look_it_up import what_was_found
from sro.application.lookup.run_lookups import Answers, Looked
from sro.domain.lookup.plan import Lookup, Plan

EQUIPMENT = "/data/WM/wm/equipmentTypes"
URL = f"https://wms.example{EQUIPMENT}?siteId=SG"


def _lookup(find: str, target: str = EQUIPMENT) -> Lookup:
    return Lookup(system="wms", how="call", target=target, find=find)


def _list(*codes: str, total: int | None = None) -> str:
    body: dict[str, object] = {
        "data": [{"equipmentType": c, "description": f"{c} desc"} for c in codes]
    }
    if total is not None:
        body["totalCount"] = total
    return json.dumps(body)


def _said(lookup: Lookup, body: str | None) -> str:
    read = read_answer(body, url=URL) if body else None
    one = Looked(lookup=lookup, ok=True, url=URL, read=read)
    return what_was_found(Answers(plan=Plan(question="q", lookups=(lookup,)), looked=(one,)))


def test_a_list_without_the_record_says_no_not_how_many_there_are() -> None:
    said = _said(_lookup("ZWOYBN"), _list("PALLET", "CART", "FORKLIFT"))
    assert said.startswith("No"), said
    assert "ZWOYBN" in said


def test_a_list_with_the_record_says_yes_whatever_the_case() -> None:
    said = _said(_lookup("zwoybn"), _list("PALLET", "ZWOYBN"))
    assert said.startswith("Yes") and "ZWOYBN" in said


def test_a_value_inside_a_longer_one_is_not_the_one_asked_for() -> None:
    assert _said(_lookup("CART"), _list("CARTON", "PALLET")).startswith("No")


def test_a_list_that_is_only_a_page_cannot_say_no() -> None:
    said = _said(_lookup("ZWOYBN"), _list("A", "B", total=88))
    assert "could not tell" in said.lower(), said


def test_a_list_of_something_else_is_still_only_about_what_it_lists() -> None:
    said = _said(_lookup("ZWOYBN", "/data/WM/wm/warehouseEquipmentAccesses"), _list("A"))
    assert said.startswith("No") and "warehouse equipment access" in said


def test_a_read_that_is_not_records_could_not_tell() -> None:
    # a 404 by key falls back to a screenshot: ok, with nothing read
    said = _said(_lookup("ZWOYBN", f"{EQUIPMENT}/ZWOYBN"), None)
    assert "could not tell" in said.lower(), said


def test_a_question_that_names_no_value_is_answered_as_before() -> None:
    said = _said(_lookup(""), _list("A", "B"))
    assert said.startswith("There are 2")
