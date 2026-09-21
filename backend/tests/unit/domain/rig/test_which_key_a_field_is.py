"""Which body key a screen's name is posted as.

The join `write_plan` refuses to guess, answered rather than guessed. That
module's argument is exact and stands: a body key is not derivable from a
label, and a suffix match is ambiguous on the only real body there is --
`palletBuildingConsolidateBy` writes and `displayedPalletBuildingConsolidateBy`
does nothing, and a control ending `…ConsolidateBy` matches both.

What is different here is the source. The dictionary is a DECLARATION --
somebody wrote down that `longDescription` is labelled `Customer Type
Description` -- and reading a declaration is not inferring a correspondence
from the shape of two strings.
"""

from __future__ import annotations

from sro.domain.execution.field_notes import keys_named

DICTIONARY = {
    "customerType": {"labels": ["Customer Type"], "max_length": 60},
    "longDescription": {"labels": ["Customer Type Description", "Description"]},
    "department": {"labels": ["Department"]},
    # The counter-example from `write_plan`, in the shape it really has.
    "palletBuildingConsolidateBy": {"labels": ["Pallet Building"]},
    "displayedPalletBuildingConsolidateBy": {"labels": ["Pallet Building"]},
}


def test_a_screen_name_is_joined_to_the_key_that_posts_it() -> None:
    assert keys_named(["Customer Type Description"], DICTIONARY) == {
        "Customer Type Description": "longDescription"
    }


def test_a_label_two_keys_answer_to_decides_nothing() -> None:
    """`Description` is a label on ten different keys on this deployment, and a
    guess between them is a value written into a slot nobody chose."""
    assert keys_named(["Pallet Building"], DICTIONARY) == {}


def test_the_screens_own_form_settles_what_the_dictionary_cannot() -> None:
    """It says what THIS screen calls THIS slot, where the dictionary says what
    the vendor calls it everywhere."""
    form = {"palletBuildingConsolidateBy": {"labels": ["Pallet Building"]}}

    assert keys_named(["Pallet Building"], form, DICTIONARY) == {
        "Pallet Building": "palletBuildingConsolidateBy"
    }


def test_the_screens_own_form_wins_where_both_answer_and_disagree() -> None:
    """Not an ambiguity -- two sources, each certain, and they differ. The form
    is the one standing in front of the operator: the dictionary says what the
    vendor calls this field across every screen that posts it, and a screen may
    post it as something else."""
    form = {"csttypDescription": {"labels": ["Customer Type Description"]}}

    assert keys_named(["Customer Type Description"], form, DICTIONARY) == {
        "Customer Type Description": "csttypDescription"
    }


def test_a_name_that_is_already_a_key_answers_itself() -> None:
    """A request naming `longDescription` outright has named the key."""
    assert keys_named(["longDescription"], DICTIONARY) == {"longDescription": "longDescription"}


def test_punctuation_and_case_are_not_a_different_name() -> None:
    """`Customer Type:` and `customer type` are one name -- a screen and a
    mined parameter disagree about both."""
    assert keys_named(["customer type:"], DICTIONARY) == {"customer type:": "customerType"}


def test_a_name_nothing_declares_is_not_invented() -> None:
    assert keys_named(["Reservation Priority"], DICTIONARY) == {}


def test_nothing_asked_for_is_nothing_answered() -> None:
    assert keys_named([], DICTIONARY) == {}
    assert keys_named(["Customer Type"]) == {}
