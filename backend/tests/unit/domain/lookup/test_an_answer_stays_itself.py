"""One reader, one shape, every surface.

The lookup plane was the only read in this system that did not go through
`application.execution.answer.read_answer`. It handed the raw body on, and
each surface that drew it parsed JSON, picked columns and counted rows for
itself -- so each of them guessed, and the panel guessed badly.
"""

from __future__ import annotations

import json

from sro.application.execution.answer import read_answer
from sro.domain.lookup.answer import K_ANSWER_CHARS, K_SAMPLE, as_seen, subject_of, trimmed

WMS = "https://wms.example/data/WM/wm/customerTypes"


def _payload(rows: list[dict[str, object]]) -> str:
    return json.dumps({"@type": "ResponseBodyWrapper", "data": rows})


def _customer_types(n: int) -> list[dict[str, object]]:
    """The shape this deployment actually answers with: the fields that matter
    buried under alphabetised nulls, and a `self_uri` repeating the address."""
    return [
        {
            "URNFormat": None,
            "absoluteGroup": None,
            "allocationSearchPath": None,
            "bulkPickingFlag": False,
            "customerType": f"CT{at}",
            "longDescription": f"leaning SRO {at}",
            "self_uri": f"{WMS}/CT{at}",
        }
        for at in range(n)
    ]


def _seen(
    rows: list[dict[str, object]],
    *,
    target: str = "/data/WM/wm/customerTypes",
    asked: str = "is there a customer type called KKYT",
) -> dict:
    body = _payload(rows)
    return as_seen(
        system="WM",
        target=target,
        ok=True,
        detail="",
        answer={"status": 200, "body": body},
        read=read_answer(body, url=WMS),
        question=asked,
    )


# --- what crosses -------------------------------------------------------------


def test_records_cross_as_records_and_never_as_a_body() -> None:
    """The raw body is what every surface was guessing at. It does not travel
    for an answer that is records."""
    seen = _seen(_customer_types(3))

    assert seen["body"] is None
    assert seen["read"] is not None


def test_the_columns_are_the_ones_that_carry_something() -> None:
    """Measured on the deployment 2026-09-21, beside the warehouse's own
    screen. The WMS grid showed `Customer Type | Description`; the panel showed
    `URNFORMAT | ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` as columns of em dashes,
    because it took the first six KEYS of a payload that alphabetises."""
    columns = _seen(_customer_types(3))["read"]["columns"]

    assert "customerType" in columns
    assert "longDescription" in columns
    assert "URNFormat" not in columns, columns
    assert "absoluteGroup" not in columns, columns


def test_a_link_repeating_the_address_is_not_a_column() -> None:
    """`self_uri` says where the request was made to, which the card already
    says above the table."""
    assert "self_uri" not in _seen(_customer_types(3))["read"]["columns"]


def test_the_identifying_fields_come_first() -> None:
    """A code and a name tell one record from another; a boolean does not.
    This is the half `answer.py` does that nothing on the drawing side could:
    it is a ranking, not a filter."""
    columns = _seen(_customer_types(3))["read"]["columns"]

    assert columns.index("customerType") < columns.index("bulkPickingFlag")
    assert columns.index("longDescription") < columns.index("bulkPickingFlag")


def test_the_records_are_projected_onto_those_columns() -> None:
    first = _seen(_customer_types(2))["read"]["records"][0]

    assert first["customerType"] == "CT0"
    assert "URNFormat" not in first, "an empty field crossed the wire to be drawn as a dash"


# --- what it says -------------------------------------------------------------


def test_the_sentence_is_the_answer_a_question_wanted() -> None:
    """Deterministic -- counted and named from the payload, never summarised
    by a model, because "16" has to be 16."""
    said = _seen(_customer_types(2))["read"]["sentence"]

    assert "2 customer type" in said, said
    assert "CT0" in said


def test_one_record_is_said_in_the_singular() -> None:
    assert _seen(_customer_types(1))["read"]["sentence"].startswith("One customer type")


def test_nothing_found_says_so_rather_than_drawing_an_empty_table() -> None:
    assert "Nothing matched" in _seen([])["read"]["sentence"]


# --- what the records are OF --------------------------------------------------


def test_the_subject_comes_from_the_address_the_records_came_from() -> None:
    """The reader is handed a body and never the question, so it cannot know
    what the records are of. The address does."""
    assert subject_of("/data/WM/wm/customerTypes") == "customer type"
    assert subject_of("/data/WM/wm/suppliers") == "supplier"
    assert subject_of("/data/MCS/rpux/currencies") == "currency"


def test_a_screen_route_is_not_a_subject() -> None:
    """`#wm.config/wm.config.partners.customers.types////` names a screen, and
    "There are 50 wm.config.partners.customers.types" is a sentence nobody
    wrote on purpose."""
    assert subject_of("#wm.config/wm.config.partners.customers.types////") == ""


# --- what does not read as records --------------------------------------------


def test_a_page_of_html_keeps_its_body_and_is_cut_by_character() -> None:
    """There is nothing structural in it to cut along."""
    page = "<html>" + ("x" * K_ANSWER_CHARS) + "</html>"
    seen = as_seen(
        system="WM", target="/portal", ok=True, detail="", answer={"status": 200, "body": page}
    )

    assert seen["read"] is None
    assert seen["truncated"] is True
    assert seen["body"] == page[:K_ANSWER_CHARS]


def test_a_picture_is_not_carried() -> None:
    """Hundreds of kilobytes of base64 per screen, and what it MEANS is a
    model's question rather than a field on this shape."""
    seen = as_seen(
        system="WM",
        target="#wm.config/...",
        ok=True,
        detail="",
        answer={"image_base64": "iVBORw0KGgo=", "width": 1280, "height": 800},
    )

    assert seen["body"] is None and seen["read"] is None
    assert "image_base64" not in seen


def test_a_short_body_is_left_exactly_alone() -> None:
    assert trimmed("{}") == ("{}", False)
    assert trimmed(None) == (None, False)


# --- how much crosses ----------------------------------------------------------


def test_more_records_than_a_surface_draws_do_not_all_cross() -> None:
    """`answer.py` bounds its sample where the answer IS the product -- a
    taught read whose rows a person works from. A panel draws eight and offers
    the console for the rest."""
    seen = _seen(_customer_types(K_SAMPLE + 50))

    assert len(seen["read"]["records"]) == K_SAMPLE
    assert seen["truncated"] is True
    # And the count is still the count, not the size of what crossed.
    assert seen["read"]["counted"] == K_SAMPLE + 50


# --- answering what was asked --------------------------------------------------


def test_a_question_that_names_a_record_is_answered_with_that_record() -> None:
    """ "is there a customer type called KKYT" is a yes and a record, not a
    hundred and ten of them. It was answered "There are 110 customer type:
    leaning SRO 4 (DPP), ..." -- true, and not what anybody asked."""
    rows = [*_customer_types(40), {"customerType": "KKYT", "longDescription": "my sro is best"}]
    read = _seen(rows)["read"]

    assert read["matched"] == 1
    assert [one["customerType"] for one in read["records"]] == ["KKYT"]
    assert read["sentence"].startswith("Yes —"), read["sentence"]
    assert "KKYT" in read["sentence"]


def test_it_says_how_much_of_the_collection_that_was() -> None:
    """So a surface can offer the rest rather than pretending the answer is
    the whole of it."""
    rows = [*_customer_types(40), {"customerType": "KKYT", "longDescription": "my sro is best"}]
    read = _seen(rows)["read"]

    assert read["of"] == 41
    assert "of 41" in read["sentence"], read["sentence"]


def test_a_question_about_the_collection_still_gets_the_collection() -> None:
    read = _seen(_customer_types(5), asked="how many customer types are there")["read"]

    assert read["matched"] == 0
    assert len(read["records"]) == 5
    assert read["sentence"].startswith("There are 5 customer type")


def test_a_name_nothing_carries_is_answered_no() -> None:
    read = _seen(_customer_types(5), asked="is there a customer type called ZZZZ")["read"]

    # Nothing named, so the collection is what comes back -- and the sentence
    # is the collection's, because "no" and "you did not ask about one of
    # these" are different facts and only the records can tell them apart.
    assert read["matched"] == 0
