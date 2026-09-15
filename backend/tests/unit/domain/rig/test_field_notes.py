"""What the field dictionary knows, said to the person who taps Approve.

The claim bodies here are the shape the store actually holds -- read off
`knowledge_entries` on the QA deployment, 2026-09-16, where `customerType`'s
`field` claim carries `max_length: 60` beside its label and the screens it is
required on.
"""

from __future__ import annotations

from sro.domain.execution.field_notes import notes_on

CUSTOMER_TYPE: dict[str, object] = {
    "type": "combo",
    "labels": ["Customer Type"],
    "screens": ["Existing Customers", "Customer Types"],
    "documented": True,
    "max_length": 60,
    "required_on": ["Customer Types"],
}


def test_a_value_the_field_cannot_hold_is_said_before_the_write_goes_out() -> None:
    """The sharpest instance of the one failure the ladder cannot see: the form
    sends more than the column keeps, the warehouse answers 201, and the record
    is wrong with nothing anywhere saying so."""
    said = notes_on({"customerType": "Z" * 61}, {"customerType": CUSTOMER_TYPE})

    assert said == ("Customer Type holds 60 characters and this run supplies 61",)


def test_a_value_that_fits_is_not_worth_a_line() -> None:
    """A note beside every field is a card nobody reads. What earns a line is a
    fact that predicts a wrong record, and "it fits" predicts nothing."""
    assert notes_on({"customerType": "Z" * 60}, {"customerType": CUSTOMER_TYPE}) == ()
    assert notes_on({"customerType": "ZQ46"}, {"customerType": CUSTOMER_TYPE}) == ()


def test_a_field_nobody_wrote_down_says_nothing_rather_than_guessing() -> None:
    """Most body keys have no claim: 46 keys in the real create and 404 field
    claims across the whole system. Silence is the honest answer for a field
    the dictionary has never heard of."""
    assert notes_on({"absoluteGroup": "Z" * 400}, {"customerType": CUSTOMER_TYPE}) == ()
    assert notes_on({"customerType": "Z" * 61}, {}) == ()


def test_a_limit_that_is_not_a_length_is_not_read_as_one() -> None:
    """These bodies are hand-kept JSON read from a vendor's documentation, and
    a claim about nothing must narrow what is said rather than widen it. `True`
    is an `int` in Python, so an unchecked `max_length: true` would read as a
    one-character field and warn about every value in the body."""
    for bad in (True, 0, -1, "60", None):
        assert notes_on({"f": "value"}, {"f": {"max_length": bad}}) == (), bad


def test_the_field_is_named_the_way_the_screen_names_it() -> None:
    """The person reading this is looking at the form, where it says `Customer
    Type`. `customerType` is the API's spelling of the same field, and it is
    what to fall back on rather than nothing."""
    assert (
        "Customer Type holds"
        in notes_on({"customerType": "Z" * 61}, {"customerType": CUSTOMER_TYPE})[0]
    )
    bare = notes_on({"longDescription": "Z" * 9}, {"longDescription": {"max_length": 8}})
    assert bare == ("longDescription holds 8 characters and this run supplies 9",)
    empty = notes_on({"f": "Z" * 9}, {"f": {"max_length": 8, "labels": ["", "  "]}})
    assert empty == ("f holds 8 characters and this run supplies 9",)


def test_every_field_that_will_not_fit_is_said_in_one_stable_order() -> None:
    """Two fields over the limit is two lines, and the order is the body's own
    so a card does not reshuffle itself between polls."""
    known = {"b": {"max_length": 2}, "a": {"max_length": 2}}

    said = notes_on({"b": "bbb", "a": "aaa"}, known)

    assert said == (
        "a holds 2 characters and this run supplies 3",
        "b holds 2 characters and this run supplies 3",
    )
