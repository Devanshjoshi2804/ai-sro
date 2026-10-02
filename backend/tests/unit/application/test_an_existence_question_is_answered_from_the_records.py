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

import pytest

from sro.application.execution.answer import read_answer
from sro.application.lookup.answer import as_seen
from sro.application.lookup.look_it_up import what_was_found
from sro.application.lookup.run_lookups import Answers, Looked
from sro.domain.lookup.plan import Lookup, Plan
from tests.unit.application.test_where_to_look_for_an_answer import CTX

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


def _body(records: list[dict[str, object]], **rest: object) -> str:
    return json.dumps({"data": records, **rest})


@pytest.mark.parametrize(
    "rest",
    [
        {"hasMore": True},
        {"next": "/page/2"},
        {"nextPage": 2},
        {"links": {"next": "/page/2"}},
    ],
)
def test_a_page_the_server_says_has_more_cannot_say_no(rest: dict[str, object]) -> None:
    body = _body([{"equipmentType": "A"}, {"equipmentType": "B"}], **rest)
    assert "could not tell" in _said(_lookup("ZWOYBN"), body).lower()


def test_a_page_with_no_total_and_a_limit_we_sent_cannot_say_no() -> None:
    read = read_answer(_list("A", "B"), url=f"{URL}&limit=2")
    one = Looked(lookup=_lookup("ZWOYBN"), ok=True, url=URL, read=read)
    said = what_was_found(Answers(plan=Plan(question="q", lookups=(one.lookup,)), looked=(one,)))
    assert "could not tell" in said.lower()


def test_a_value_in_a_column_the_display_cuts_is_still_found() -> None:
    record: dict[str, object] = {f"col{i:02d}": f"v{i}" for i in range(12)}
    record["zzzNote"] = "ZWOYBN"
    said = _said(_lookup("ZWOYBN"), _body([record]))
    assert said.startswith("Yes"), said


def test_a_value_longer_than_the_display_cut_is_still_found() -> None:
    long = "L" * 70
    assert _said(_lookup(long), _body([{"equipmentType": long}])).startswith("Yes")


def test_a_padded_value_equals_the_asked_one() -> None:
    assert _said(_lookup("Z"), _body([{"equipmentType": "Z "}])).startswith("Yes")


def test_a_no_does_not_invent_a_plural() -> None:
    said = _said(_lookup("X", "/data/WM/wm/address"), _list("A", "B"))
    assert "addresss" not in said and "categorys" not in said and said.startswith("No")


def test_the_card_does_not_say_yes_on_a_fuzzy_word() -> None:
    read = read_answer(_list("PALLET", "CART"), url=URL)
    assert read is not None
    seen = as_seen(
        system="wms",
        target=EQUIPMENT,
        ok=True,
        detail="",
        answer={"status": 200},
        read=read,
        question="is there a warehouse equipment type ZWOYBN",
        find="ZWOYBN",
    )
    card = seen["read"]
    assert isinstance(card, dict)
    assert str(card["sentence"]).startswith("No") and card["matched"] == 0


def test_the_card_says_yes_on_an_equal_record() -> None:
    read = read_answer(_list("PALLET", "CART"), url=URL)
    assert read is not None
    seen = as_seen(
        system="wms",
        target=EQUIPMENT,
        ok=True,
        detail="",
        answer={"status": 200},
        read=read,
        question="is there equipment type cart",
        find="cart",
    )
    card = seen["read"]
    assert isinstance(card, dict)
    assert str(card["sentence"]).startswith("Yes") and card["matched"] == 1


def test_a_yes_names_the_column_that_matched() -> None:
    assert "status" in _said(_lookup("ACTIVE"), _body([{"status": "ACTIVE", "equipmentType": "A"}]))


def test_several_reads_give_one_verdict_yes_if_any_found_it() -> None:
    a, b = _lookup("Z"), _lookup("Z", "/data/WM/wm/other")
    looked = (
        Looked(lookup=a, ok=True, url=URL, read=read_answer(_list("A"), url=URL)),
        Looked(lookup=b, ok=True, url=URL, read=read_answer(_list("Z"), url=URL)),
    )
    said = what_was_found(Answers(plan=Plan(question="q", lookups=(a, b)), looked=looked))
    assert said.startswith("Yes") and "No" not in said


def test_a_failed_read_that_could_have_held_it_makes_the_answer_could_not_tell() -> None:
    a, b = _lookup("Z"), _lookup("Z", "/data/WM/wm/other")
    looked = (
        Looked(lookup=a, ok=True, url=URL, read=read_answer(_list("A"), url=URL)),
        Looked(lookup=b, ok=False, url=URL, detail="timed out"),
    )
    said = what_was_found(Answers(plan=Plan(question="q", lookups=(a, b)), looked=looked))
    assert "could not tell" in said.lower() and not said.startswith("No")


def test_every_read_whole_and_lacking_it_says_one_no() -> None:
    a, b = _lookup("Z"), _lookup("Z", "/data/WM/wm/other")
    looked = (
        Looked(lookup=a, ok=True, url=URL, read=read_answer(_list("A"), url=URL)),
        Looked(lookup=b, ok=True, url=URL, read=read_answer(_list("B"), url=URL)),
    )
    said = what_was_found(Answers(plan=Plan(question="q", lookups=(a, b)), looked=looked))
    assert said.startswith("No") and said.count("No") == 1


async def test_the_value_flows_from_the_planner_to_the_sentence() -> None:
    from sro.application.lookup.look_it_up import LookItUp
    from tests.unit.application.test_where_to_look_for_an_answer import _planner
    from tests.unit.application.test_where_to_look_for_an_answer import _said as _plan

    class _Read:
        async def execute(self, ctx: object, *, plan: Plan, within: float) -> Answers:
            one = Looked(
                lookup=plan.lookups[0], ok=True, url=URL, read=read_answer(_list("A", "B"), url=URL)
            )
            return Answers(plan=plan, looked=(one,))

    planner, _ = _planner(_plan(find="ZWOYBN"))
    found = await LookItUp(planner, _Read()).execute(CTX, "is there a supplier ZWOYBN", within=5)
    assert found is not None and what_was_found(found).startswith("No")
