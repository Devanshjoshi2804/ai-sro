"""What a run keeps of the record it created, and what it refuses to keep.

`made_by` reads a create's answer and stores the handful of fields that NAME
the row it made. That is how a run can say which three records it is
responsible for, and how an undo -- the day the evidence for one exists --
addresses them by whatever the warehouse called them.

It is also a function that reads a customer's data and writes part of it onto
a row that outlives the run. So the limits matter as much as the extraction:
what is kept is short, few, and only the fields that identify.

Written because a mutation sweep found twenty-five survivors here and no test
that called it directly. It was reached only through `execute_skill`, where a
create's answer is incidental to what that test was asserting -- so every
branch below could have said something else and the suite would have agreed.
"""

from __future__ import annotations

import json

import pytest

from sro.application.execution.verify import K_NAMED, made_by


def _answered(body: object) -> dict[str, object]:
    """A call as the runner records it: the response body, as text."""
    return {"body": body if isinstance(body, str) else json.dumps(body)}


# -- what it keeps -------------------------------------------------------------


def test_it_keeps_the_fields_that_say_which_record_this_is() -> None:
    named = made_by(_answered({"equipmentTypeId": "DDD", "warehouseCode": "SG"}))

    assert named == {"equipmentTypeId": "DDD", "warehouseCode": "SG"}


@pytest.mark.parametrize(
    "key",
    ["equipmentTypeId", "workAreaCode", "supplierNumber", "customerName", "vaultKey"],
)
def test_the_suffix_is_read_case_insensitively_because_a_warehouse_names_its_own_way(
    key: str,
) -> None:
    assert made_by(_answered({key: "x"})) == {key: "x"}


def test_a_number_is_an_identifier_too() -> None:
    """`supplierNumber: 4021` is how a warehouse answers, and a run that
    could not name a record because its id arrived unquoted would be a run
    nobody can follow."""
    assert made_by(_answered({"supplierNumber": 4021})) == {"supplierNumber": "4021"}


# -- what it refuses -----------------------------------------------------------


def test_a_field_that_does_not_identify_is_not_kept() -> None:
    """The line this function exists to hold. `description` and `address` are
    a customer's data; keeping them would put a row of somebody's warehouse on
    a record that outlives the run."""
    named = made_by(_answered({"id": "A1", "description": "Aisle 4, cold store", "qty": 12}))

    assert named == {"id": "A1"}


def test_a_value_too_long_to_be_an_identifier_is_not_one() -> None:
    """Sixty-four characters. Past that it is a sentence, and a sentence in
    this field is a paragraph of somebody's data stored for as long as the
    tenant keeps evidence."""
    assert made_by(_answered({"itemName": "x" * 64})) == {"itemName": "x" * 64}
    assert made_by(_answered({"itemName": "x" * 65})) == {}


def test_a_blank_value_names_nothing() -> None:
    assert made_by(_answered({"id": "   "})) == {}


def test_it_stops_after_a_handful_because_a_dozen_names_is_a_list() -> None:
    many = {f"thing{index}Id": str(index) for index in range(K_NAMED + 4)}

    assert len(made_by(_answered(many))) == K_NAMED


@pytest.mark.parametrize(
    ("body", "why"),
    [
        (None, "a call with no body at all"),
        ("", "an empty body"),
        ("   ", "a body of whitespace"),
        ("not json", "a body that is not json"),
        ("[1, 2, 3]", "a json array, which names nothing"),
        ('"a string"', "a json string"),
        ("null", "json null"),
    ],
)
def test_an_answer_it_cannot_read_names_nothing_rather_than_raising(body: object, why: str) -> None:
    """Every one of these arrives from a warehouse nobody controls, and a
    create whose answer could not be parsed still happened -- so this returns
    nothing and lets the step be judged on its status, rather than failing the
    run over the shape of a reply."""
    assert made_by({"body": body}) == {}, why


def test_a_call_with_no_body_key_at_all_names_nothing() -> None:
    assert made_by({}) == {}


def test_a_value_that_is_neither_text_nor_a_number_is_skipped() -> None:
    """A nested object under an identifying name is not an identifier, and
    `str()` of it would store a dict's repr on the run."""
    assert made_by(_answered({"ownerId": {"nested": "thing"}, "lineId": "L9"})) == {"lineId": "L9"}
