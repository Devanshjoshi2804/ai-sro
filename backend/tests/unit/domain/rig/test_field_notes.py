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


# What the form itself says, where it disagrees with the manual


FROM_THE_FORM = {
    "labels": ["Customer Type"],
    "max_length": 4,
    "required": True,
    "observed": True,
}


def test_the_form_s_own_limit_is_the_one_a_person_is_shown() -> None:
    """Measured on QA 2026-09-16, and the disagreement is the whole point.

    The dictionary says `customerType` holds 60 characters. The Customer Types
    create form -- captured from the real form an operator uses -- says 4. The
    ledger's own gotcha, somebody's measurement, says `csttyp truncates at 4
    chars`. Two of the three agree and the card was reading the third, so a
    request for `NEWSROTEST` would have been sent, truncated to `NEWS`,
    answered 201, and read back as the record the system actually made.
    """
    said = notes_on({"customerType": "NEWSROTEST"}, {"customerType": FROM_THE_FORM})

    assert len(said) == 1
    assert "holds 4 characters and this run supplies 10" in said[0]
    # And which of the two sources they are reading, because they disagree.
    assert "what the form itself says" in said[0]


def test_a_value_the_manual_would_have_passed_is_still_a_note() -> None:
    """`Z` * 10 fits the documented 60 and does not fit the real 4. A card that
    read only the manual said nothing at all about it."""
    documented = {"labels": ["Customer Type"], "max_length": 60}

    assert notes_on({"customerType": "Z" * 10}, {"customerType": documented}) == ()
    assert len(notes_on({"customerType": "Z" * 10}, {"customerType": FROM_THE_FORM})) == 1


def test_a_field_the_form_requires_and_the_write_omits_earns_a_line() -> None:
    """On a replay that is a demonstration which did not fill it. A note and
    not a refusal, for the module's own reason: the demonstration DID land, so
    the person approving is owed the fact rather than a blocked run."""
    said = notes_on(
        {"customerType": "GPP"},
        {
            "customerType": FROM_THE_FORM,
            "longDescription": {
                "labels": ["Customer Type Description"],
                "required": True,
                "observed": True,
            },
        },
    )

    assert said == (
        "Customer Type Description is required on this form and this run sends nothing",
    )


def test_a_field_the_form_requires_and_the_write_carries_says_nothing() -> None:
    """ "This field is required and you supplied it" is not news, and a note
    beside every field is a card nobody reads."""
    assert (
        notes_on(
            {"customerType": "GPP"},
            {"customerType": FROM_THE_FORM},
        )
        == ()
    )


# The four a mutation sweep found, each a real behaviour nothing pinned


def test_one_field_with_nothing_known_does_not_silence_the_next() -> None:
    """`continue`, not `break`. The claims come back by key and a write fills
    several: a body key the dictionary has never heard of must skip its own
    line rather than end the reading of every field after it."""
    said = notes_on(
        {"aaaUnknown": "x", "customerType": "NEWSROTEST"},
        {"customerType": FROM_THE_FORM},
    )

    assert len(said) == 1, "a key with no claim behind it took the next field's note with it"


def test_a_field_already_sent_does_not_silence_a_required_one_after_it() -> None:
    """The same rule in the second loop: a required field is looked for across
    every claim, and the ones the write DOES carry are skipped one at a time."""
    said = notes_on(
        {"customerType": "GPP"},
        {
            "customerType": FROM_THE_FORM,
            "longDescription": {"labels": ["Customer Type Description"], "required": True},
        },
    )

    assert said == (
        "Customer Type Description is required on this form and this run sends nothing",
    )


def test_which_source_the_limit_came_from_is_the_end_of_the_sentence() -> None:
    """Asserted exactly, because the two sources disagree and the phrase is
    what tells a person which one they are reading."""
    (said,) = notes_on({"customerType": "NEWSROTEST"}, {"customerType": FROM_THE_FORM})

    assert said.endswith("supplies 10 (what the form itself says)")


def test_a_required_field_with_no_label_is_named_by_its_body_key() -> None:
    """A claim the form captured without a label still has to be sayable. The
    body key is what the API calls it, which is worse than the screen's word
    and far better than nothing."""
    said = notes_on({}, {"longDescription": {"required": True, "observed": True}})

    assert said == ("longDescription is required on this form and this run sends nothing",)


def test_a_field_that_holds_one_character_is_a_field_like_any_other() -> None:
    """`> 0`, not `> 1`. A one-character flag column is real -- this base has
    several -- and a value of two characters does not fit in it."""
    assert notes_on({"flag": "YN"}, {"flag": {"labels": ["Flag"], "max_length": 1}}) == (
        "Flag holds 1 characters and this run supplies 2",
    )
