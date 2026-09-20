"""Which records a question named, decided once rather than per surface.

The panel worked this out in JavaScript, twice. First by matching every word
of the question against every value, which promoted the forty records whose
description contains `type` ahead of the one called KKYT. Then by dropping
words that match too much of the result -- the right rule, in the wrong place:
the console draws the same answers and a model reading one has the same
problem.
"""

from __future__ import annotations

from sro.domain.lookup.naming import asked_for, named, names, telling

TYPES = [
    {"longDescription": f"leaning new SRO type {at}", "resourceId": f"CT{at}"} for at in range(40)
] + [
    {"longDescription": "my sro is best", "resourceId": "KKYT"},
    {"longDescription": "Customer Outbound Orders", "resourceId": "COO"},
    {"longDescription": "DISTRIBUTOR", "resourceId": "DSTR"},
]


def test_the_record_the_question_named() -> None:
    found = named("is there a customer type called KKYT", TYPES, "customer type")

    assert [one["resourceId"] for one in found] == ["KKYT"]


def test_a_word_that_describes_the_whole_result_names_nothing_in_it() -> None:
    """Measured on the deployment 2026-09-21: over 110 customer types, `type`
    appears in forty descriptions and `kkyt` in one. Matching on `type`
    promoted forty records ahead of the one asked about."""
    assert telling(("type",), TYPES) == ()
    assert telling(("kkyt",), TYPES) == ("kkyt",)


def test_a_question_about_the_collection_names_nothing() -> None:
    """ "how many customer types are there" wants all of them, and a filter
    that answered with one would be worse than no filter."""
    assert named("how many customer types are there", TYPES, "customer type") == ()


def test_a_name_nothing_carries_matches_nothing() -> None:
    """A yes/no question about something absent is a NO, and the difference
    between that and "nothing was asked" is the whole of what a caller reads:
    no words that tell -> (), a word that tells and matches nothing -> ()."""
    assert named("is there a customer type called ZZZZ", TYPES, "customer type") == ()


def test_the_collections_own_name_is_not_a_search_term() -> None:
    """ "is there a CUSTOMER type called KKYT" also matches the record
    described `Customer Outbound Orders`, which nobody asked about and which
    pushes the answer to second place. `customer` picks out one record of
    forty-three -- few enough to look distinguishing, and it is not."""
    without = named("is there a customer type called KKYT", TYPES)
    with_it = named("is there a customer type called KKYT", TYPES, "customer type")

    assert [one["resourceId"] for one in without] == ["KKYT", "COO"]
    assert [one["resourceId"] for one in with_it] == ["KKYT"]


def test_field_names_are_never_matched() -> None:
    """`customer` and `type` are in every column name on this endpoint and in
    none of the records. Matching names would pick every record, which is the
    same as picking none."""
    assert names({"customerType": "GPP"}, ("customertype",)) is False
    assert names({"customerType": "GPP"}, ("gpp",)) is True


def test_a_value_that_is_not_a_word_is_not_searched() -> None:
    """A nested object or a list is structure, not something somebody typed."""
    assert names({"a": {"deep": "kkyt"}, "b": ["kkyt"]}, ("kkyt",)) is False


def test_the_words_of_a_question_that_could_name_anything() -> None:
    assert asked_for("is there a customer type called KKYT") == (
        "customer",
        "type",
        "kkyt",
    )
    # Two letters matches inside half the values in a warehouse.
    assert asked_for("is it ok") == ()


def test_nothing_asked_names_nothing() -> None:
    assert named("", TYPES) == ()
    assert named("how many", []) == ()
