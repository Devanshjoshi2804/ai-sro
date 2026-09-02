import pytest

from sro.application.induction.diff import Parameterisation, Substitution
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import (
    _refuse_an_unfillable_input,
    _wanted,
    with_options,
)
from sro.application.induction.lookups import Wanted, _listing_of, filtered_on, plan
from sro.application.induction.sites import JsonBodySite, as_a_filter
from sro.domain.skill.lookup import Options
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.application.lookup_fixtures import a_click, a_frame, a_read, a_write


def test_a_read_the_operator_filtered_names_its_column() -> None:
    read = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]'
    )

    assert filtered_on(read) == "addressName"


def test_an_unfiltered_page_names_nothing() -> None:
    assert filtered_on(a_read("https://wms.example/addresses?offset=0&limit=50")) is None


def test_a_read_filtered_on_two_columns_names_nothing() -> None:
    """Two columns is two answers about how the record was found, and the rule
    is that disagreement refuses."""
    read = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"},'
        '{"column":"city","operator":"EQ","value":"BURLINGTON"}]'
    )

    assert filtered_on(read) is None


def test_an_empty_filter_slot_names_nothing() -> None:
    """`_filter_terms` calls an empty list a filter -- it says the endpoint
    takes one. It does not say which column anybody searched."""
    assert filtered_on(a_read("https://wms.example/addresses?query=[]")) is None


def test_the_listing_is_found_in_a_doing_outside_the_pair() -> None:
    """The two doings that align hold one call each: the write. The doing that
    holds the address listing is the one alignment rejected."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    listing_b = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"also"}]',
        [{"addressId": "A1", "addressName": "also test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    pair_a = (a_frame(write),)
    # pair_b also carries a listing with the wanted value, positioned before its
    # own write -- exactly the shape `_first_mutation` would happily search. It
    # exists only to prove index 1 is bounded by `step_index` (0, excluding it)
    # rather than falling through to `other`'s rule.
    #
    # It is a *filtered* read of the same collection, deliberately. An
    # unfiltered one would be excluded twice over -- once by the bound and once
    # by the preference for a filtered listing -- and reverting either rule
    # alone would leave this test green, which is a guard that guards nothing.
    pair_b = (a_frame(listing_b), a_frame(write))
    other = (a_frame(listing), a_frame(write))

    # Both aligned doings (indices 0 and 1) are bounded by `step_index` -- one
    # holds only the write, the other holds a listing that bound must exclude.
    # `other`, at index 2, is outside the pair `_listing_of`'s `at < 2` test
    # distinguishes, so it is searched up to its own first mutation instead.
    found = _listing_of((pair_a, pair_b, other), value="A1", step_index=0)

    assert found is not None
    assert found[0].url == listing.url


def test_the_listing_is_the_read_the_operator_filtered_not_the_page_before_it() -> None:
    """The dialog opens on page one and only then does anybody type. Whichever
    read came first, `Options.url` has to be the filtered one: `as_a_filter`
    re-aims a query by replacing the terms of a filter the URL already carries,
    so a dropdown built on `?offset=0&limit=50` narrows nothing at run time
    however well the searched column was chosen.
    """
    page = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [
            {"addressId": "A1", "addressName": "test", "city": "BURLINGTON"},
            {"addressId": "A2", "addressName": "other", "city": "OAKVILLE"},
        ],
    )
    searched = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    run = (a_frame(page), a_frame(searched), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert "query=" in planned[0].options.url
    assert "offset" not in planned[0].options.url


def test_a_read_after_that_doing_s_own_write_is_not_the_listing() -> None:
    """The grid refreshing after a save shows the record that was just created.
    Reading the id back out of it proves nothing about how it was chosen."""
    after = a_read("https://wms.example/addresses", [{"addressId": "A1", "addressName": "test"}])
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert _listing_of(((a_frame(write), a_frame(after)),), value="A1", step_index=None) is None


def test_a_column_the_write_never_sends_can_still_identify_the_record() -> None:
    """The create sends `codAddressId` and nothing else off that record. Of the
    address's own fields the write sends none, so the write-sent rule can never
    be satisfied for a value that was picked rather than typed."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert planned[0].options.value == "addressId"


def test_a_picked_id_no_doing_ever_searched_for_stays_a_question() -> None:
    listing = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
            run_a=(a_frame(listing), a_frame(write)),
            run_b=(a_frame(listing), a_frame(write)),
        )
        == ()
    )


def test_two_doings_that_searched_different_columns_plan_nothing() -> None:
    by_name = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    by_city = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"BUR"}]',
        [{"addressId": "A2", "addressName": "other", "city": "BURLINGTON"}],
    )
    write_a = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    write_b = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A2"})

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
            run_a=(a_frame(by_name), a_frame(write_a)),
            run_b=(a_frame(by_city), a_frame(write_b)),
        )
        == ()
    )


def test_a_filtered_column_absent_from_the_picked_record_plans_nothing() -> None:
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"nickname","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
            run_a=(a_frame(listing), a_frame(write)),
            run_b=(a_frame(listing), a_frame(write)),
        )
        == ()
    )


def test_a_read_filtered_on_a_column_the_record_lacks_is_not_the_listing() -> None:
    """`nickname` is a column of the endpoint, not a field of the row that came
    back. Promoting that read to `Options.url` makes `as_a_filter` succeed and
    sends the live query out as `column=addressName` riding a filter shape the
    demonstration built for `nickname` -- a real query to the warehouse system
    filtered on a column nothing proved that endpoint accepts.

    The unfiltered page wins instead, and `search` stays empty: the field the
    write happened to send is not the field the endpoint was shown filtering
    on, and ADR 004 has no other evidence to offer here.
    """
    page = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [
            {"addressId": "A1", "addressName": "test"},
            {"addressId": "A2", "addressName": "other"},
        ],
    )
    by_nickname = a_read(
        'https://wms.example/addresses?query=[{"column":"nickname","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "addressName": "test"},
    )
    run = (a_frame(page), a_frame(by_nickname), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.label == ("addressName",)
    assert "nickname" not in planned[0].options.url
    # Which is what makes the dropdown safe: the page carries no filter, so
    # nothing at run time can re-aim one at a column the endpoint was never
    # shown accepting. The whole page is fetched and narrowed in the console.
    options = planned[0].options
    assert as_a_filter(options.url, column=options.search or "", placeholder="x") is None


def test_a_listing_nothing_proved_a_column_for_is_not_searched_on_one() -> None:
    """The same evidence with no unfiltered page behind it. `Options.url` can
    only be the read filtered on `nickname`, and that read *can* be re-aimed --
    so `search` has to be empty, or the console sends the warehouse system a
    live query filtered on `addressName` in a shape only `nickname` was ever
    seen in. The field the write sent is not evidence about how the endpoint
    is asked."""
    by_nickname = a_read(
        'https://wms.example/addresses?query=[{"column":"nickname","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "addressName": "test"},
    )
    run = (a_frame(by_nickname), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.label == ("addressName",)
    assert planned[0].options.search is None


def test_the_record_is_not_labelled_by_the_id_it_is_being_looked_up_by() -> None:
    """A dialog that filters on the id column says nothing about how a person
    finds the record: a dropdown reading `A1 -> A1` asks the operator for the
    very id the lookup exists to spare them."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressId","operator":"EQ","value":"A1"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
            run_a=(a_frame(listing), a_frame(write)),
            run_b=(a_frame(listing), a_frame(write)),
        )
        == ()
    )


def test_a_value_unique_only_because_the_read_was_filtered_is_not_a_label() -> None:
    """The listing the operator picked from returned one row, so every field on
    it is trivially unique. The unfiltered read of the same collection is what
    says whether the value tells one record from another."""
    narrow = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    wide = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [
            {"addressId": "A1", "addressName": "test", "city": "BURLINGTON"},
            {"addressId": "A2", "addressName": "other", "city": "BURLINGTON"},
        ],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "city": "BURLINGTON"},
    )
    run = (a_frame(narrow), a_frame(wide), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    # `city` is sent by the write and unique in the one row the filter returned,
    # and shared by both addresses in the read that shows the collection.
    assert planned[0].options.label == ("addressName",)


def test_a_read_of_another_collection_does_not_name_the_search_column() -> None:
    """The carriers grid was filtered on `name`, and the row it returned carries
    the address id. Letting it vote re-aims the ADDRESS query at a column only
    the CARRIERS endpoint was ever shown to accept."""
    addresses = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [{"addressId": "A1", "addressName": "test", "name": "WAREHOUSE 4"}],
    )
    carriers = a_read(
        'https://wms.example/carriers?query=[{"column":"name","operator":"EQ","value":"x"}]',
        [{"carrierId": "C1", "name": "x", "codAddressId": "A1"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    run = (a_frame(addresses), a_frame(carriers), a_frame(write))

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
            run_a=run,
            run_b=run,
        )
        == ()
    )


def test_a_page_that_excludes_the_picked_record_does_not_judge_it() -> None:
    """Page two is the wider read and holds none of the picked row's values, so
    judging uniqueness against it makes every field on that row unique nowhere
    -- and silently unplans the lookups the write-sent rule planned before."""
    page_one = a_read(
        "https://wms.example/addresses?offset=0&limit=1",
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    page_two = a_read(
        "https://wms.example/addresses?offset=1&limit=1",
        [
            {"addressId": "A2", "addressName": "other", "city": "OAKVILLE"},
            {"addressId": "A3", "addressName": "third", "city": "MILTON"},
        ],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "addressName": "test"},
    )
    run = (a_frame(page_one), a_frame(page_two), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.label == ("addressName",)


def test_a_filtered_read_after_the_write_does_not_name_the_search_column() -> None:
    """The grid refreshing after a save is filtered on whatever the operator
    left in the box. `_listing_of` already refuses that evidence; the column
    rule must refuse it on the same bound, or the two disagree about what a
    demonstration proved."""
    listing = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    refresh = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"BUR"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    run = (a_frame(listing), a_frame(write), a_frame(refresh))

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
            run_a=run,
            run_b=run,
        )
        == ()
    )


def test_the_searched_column_leads_the_fields_the_write_also_sent() -> None:
    """A dropdown whose first column is not the one being searched reads as a
    mistake, so the operator's own column goes in front of the write-sent ones
    rather than behind them.

    These frames carry no on-screen text, so this proves only the order the two
    sources of `usable` are assembled in. That the display heuristic cannot then
    undo that order -- the part that decides `Options.search` -- is guarded by
    `test_what_the_operator_read_on_screen_cannot_displace_what_they_searched_by`.
    """
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"BUR"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "addressName": "test"},
    )

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
    )

    assert len(planned) == 1
    assert planned[0].options.search == "city"
    assert planned[0].options.label == ("city", "addressName")


def test_what_the_operator_read_on_screen_cannot_displace_what_they_searched_by() -> None:
    """`_seen_on_screen` is a display heuristic and may only order the rest of
    the label. Letting it reach the front re-aims the live query at a column
    nothing ever proved the endpoint accepts, and throws away the one the
    demonstration filtered on -- the inference ADR 004 forbids.

    The operator searched by `addressName` and clicked a row reading
    "BURLINGTON", which is the `city` the write also sent.
    """
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "city": "BURLINGTON"},
    )
    run = (a_frame(listing), a_click("BURLINGTON"), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert planned[0].options.label == ("addressName", "city")


def test_the_field_the_operator_read_on_screen_leads_the_one_they_never_saw() -> None:
    """Both `city` and `addressName` are sent by the write and unique in the
    collection, and the record carries `city` first. The operator picked the row
    by reading "0 C TANNER" off it, so that is the field the dropdown leads
    with -- a list whose first column is one nobody ever looked at reads as the
    wrong list.

    Nothing was filtered here, so no searched column pins the front of the
    label: the order is the display heuristic's alone, which is the only shape
    where it is observable at all.
    """
    page = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [{"addressId": "A1", "city": "BURLINGTON", "addressName": "0 C TANNER"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "city": "BURLINGTON", "addressName": "0 C TANNER"},
    )
    run = (a_frame(page), a_click("0 C TANNER"), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.label == ("addressName", "city")


def test_a_search_that_did_not_return_the_record_does_not_dissent() -> None:
    """The operator searched the city first, got somebody else's address, and
    searched again by name. A read that never returned the record they went on
    to pick says nothing about how they found it -- and if it were allowed to
    speak it would count as disagreement and kill the lookup."""
    missed = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"BUR"}]',
        [{"addressId": "A2", "addressName": "other", "city": "BURLINGTON"}],
    )
    found = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "OAKVILLE"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    run = (a_frame(missed), a_frame(found), a_frame(write))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=2),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"


def test_the_refresh_after_the_save_still_says_how_many_share_a_value() -> None:
    """How many addresses are in BURLINGTON is a fact about the collection, not
    about what the operator did in what order. The grid refreshing after the
    save is a perfectly good witness to it, and excluding it calls a value
    shared by two records unique and labels the dropdown by it."""
    narrow = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write(
        "https://wms.example/carrierCrossReferences",
        {"codAddressId": "A1", "city": "BURLINGTON"},
    )
    refresh = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [
            {"addressId": "A1", "addressName": "test", "city": "BURLINGTON"},
            {"addressId": "A2", "addressName": "other", "city": "BURLINGTON"},
        ],
    )
    run = (a_frame(narrow), a_frame(write), a_frame(refresh))

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=run,
        run_b=run,
    )

    assert len(planned) == 1
    assert planned[0].options.label == ("addressName",)


def test_a_value_that_varies_gets_the_dropdown_a_constant_would_have() -> None:
    """A picked id that differs between doings needs the list more than one that
    does not: the operator must supply a different address each time, and they
    cannot type an id."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}, {"addressId": "A2", "addressName": "second"}],
    )
    planned = plan(
        (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
        run_a=(a_frame(listing), a_frame(a_write("https://wms.example/x", {"codAddressId": "A1"}))),
        run_b=(a_frame(listing), a_frame(a_write("https://wms.example/x", {"codAddressId": "A2"}))),
    )

    assert [p.field for p in planned] == ["cod_address_id"]


def test_two_values_from_two_different_collections_are_not_one_lookup() -> None:
    """One dropdown cannot offer both records: they are two lists."""
    addresses = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}],
    )
    clients = a_read(
        'https://wms.example/clients?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A2", "addressName": "second"}],
    )

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
            run_a=(
                a_frame(addresses),
                a_frame(a_write("https://wms.example/x", {"codAddressId": "A1"})),
            ),
            run_b=(
                a_frame(clients),
                a_frame(a_write("https://wms.example/x", {"codAddressId": "A2"})),
            ),
        )
        == ()
    )


def test_a_value_no_doing_can_explain_gets_no_lookup_for_the_one_that_can() -> None:
    """Run B's id is in no listing at all. Half a list is not a list."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}],
    )

    assert (
        plan(
            (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
            run_a=(
                a_frame(listing),
                a_frame(a_write("https://wms.example/x", {"codAddressId": "A1"})),
            ),
            run_b=(
                a_frame(listing),
                a_frame(a_write("https://wms.example/x", {"codAddressId": "A2"})),
            ),
        )
        == ()
    )


def test_a_parameter_the_diff_proved_is_offered_a_lookup() -> None:
    """The call site's job: a value that varied reaches `plan` at all, carrying
    both doings' values and the step that sent them."""
    parameterisation = Parameterisation(
        parameters=(
            Parameter(
                name="cod_address_id",
                kind=ParameterKind.INPUT,
                observed_values=("A1", "A2"),
            ),
            Parameter(
                name="made_by_a_step",
                kind=ParameterKind.DERIVED,
                observed_values=("D1",),
                source_step_index=0,
            ),
        ),
        substitutions={
            1: (
                Substitution(site=JsonBodySite("/codAddressId"), parameter="cod_address_id"),
                # Substituted the same way, and still not offered: nobody
                # supplies a derived value, so no dropdown could help.
                Substitution(site=JsonBodySite("/madeBy"), parameter="made_by_a_step"),
            )
        },
    )

    assert _wanted(parameterisation) == (
        Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),
    )


def test_a_field_one_doing_left_out_is_offered_with_the_one_value_seen() -> None:
    """`observed_values` holds one value when a doing omitted the field."""
    parameterisation = Parameterisation(
        parameters=(
            Parameter(name="cod_address_id", kind=ParameterKind.INPUT, observed_values=("A1",)),
        ),
        substitutions={
            2: (Substitution(site=JsonBodySite("/codAddressId"), parameter="cod_address_id"),)
        },
    )

    assert _wanted(parameterisation) == (
        Wanted(field="cod_address_id", values=("A1",), step_index=2),
    )


def test_a_parameter_substituted_at_two_steps_is_bounded_by_the_earliest() -> None:
    """A create and a later update both send the same picked id, so the diff
    records the substitution at both steps. The lookup still has to be planned
    from the read that came before the *first* of them -- the create -- not the
    last: bounding the search at the later step lets a refresh that happened
    after the create in between leak in as a second, disagreeing search column,
    and the whole lookup gets refused instead of finding `addressName`."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "OAKVILLE"}],
    )
    create = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    refresh = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"OAK"}]',
        [{"addressId": "A1", "addressName": "test", "city": "OAKVILLE"}],
    )
    update = a_write("https://wms.example/carrierCrossReferences/1", {"codAddressId": "A1"})
    run = (a_frame(listing), a_frame(create), a_frame(refresh), a_frame(update))

    parameterisation = Parameterisation(
        parameters=(
            Parameter(name="cod_address_id", kind=ParameterKind.INPUT, observed_values=("A1",)),
        ),
        substitutions={
            1: (Substitution(site=JsonBodySite("/codAddressId"), parameter="cod_address_id"),),
            3: (Substitution(site=JsonBodySite("/codAddressId"), parameter="cod_address_id"),),
        },
    )

    planned = plan(_wanted(parameterisation), run_a=run, run_b=run)

    assert len(planned) == 1, "the lookup was refused -- bounded by the later step, not the earlier"
    assert planned[0].options.search == "addressName"


def _version_asking_for(parameter: Parameter) -> SkillVersion:
    """A skill whose one step neither types nor chooses this parameter -- the
    shape the refusal was written against."""
    step = f.step(
        network_plan=f.network_plan(url=Template("https://wms.example/x"), body=None),
        ui_plan=f.ui_plan(),
    )
    return f.skill_version(steps=(step,), parameters=(parameter,))


def test_a_parameter_that_carries_its_list_is_something_an_operator_can_answer() -> None:
    """The whole point of the branch. Planning a perfect dropdown and then
    refusing the skill over the same field leaves the feature inert for the
    case it was built for: the console draws the list, fetches it from the
    endpoint the screen used, and the operator picks it the way they did when
    they taught it. That is what fillable means."""
    with_a_list = Parameter(
        name="cod_address_id",
        kind=ParameterKind.INPUT,
        absent_as="null",
        options=Options(
            url="https://wms.example/addresses", label=("addressName",), value="addressId"
        ),
    )

    _refuse_an_unfillable_input(_version_asking_for(with_a_list))


def test_the_same_parameter_without_a_list_is_still_refused() -> None:
    """The guard is not proved by the direction that passes. Strip the options
    and nothing on any medium can produce the id, so the refusal stands."""
    without_a_list = Parameter(name="cod_address_id", kind=ParameterKind.INPUT, absent_as="null")

    with pytest.raises(InductionFailed, match="type or choose"):
        _refuse_an_unfillable_input(_version_asking_for(without_a_list))


def test_attaching_a_dropdown_does_not_downgrade_what_two_runs_proved() -> None:
    """`Evidence` says how firmly we know this is a parameter; `options` says
    where its value comes from. They are different questions."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}],
    )
    write = a_write("https://wms.example/x", {"codAddressId": "A1"})
    (found,) = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
    )
    parameter = Parameter(name="cod_address_id", kind=ParameterKind.INPUT)  # Evidence.PROVEN

    assert with_options((parameter,), (found,))[0].evidence is Evidence.PROVEN
    assert with_options((parameter,), (found,))[0].options is not None


def test_the_shape_that_refused_a_whole_skill_now_induces_one() -> None:
    """Four doings of a carrier cross reference. The two that align hold one
    call each; the address listing is in a third. Before these rules the skill
    was refused whole -- `_refuse_an_unfillable_input` -- because the operator
    would have been asked to recite `A000278094`."""
    searched = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A000278094", "addressName": "0 C TANNER", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A000278094"})

    planned = plan(
        (Wanted(field="cod_address_id", values=("A000278094",), step_index=0),),
        run_a=(a_frame(write),),
        run_b=(a_frame(write),),
        others=((a_frame(searched), a_frame(write)),),
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert planned[0].options.value == "addressId"
    assert "addresses" in planned[0].options.url

    # And the refusal the name of this test cites is the one actually run. A
    # planned lookup that still refuses the skill is the whole feature being
    # inert for the case it was built for, so the end of the story is asserted
    # here rather than assumed from the three fields above.
    asked = Parameter(
        name="cod_address_id",
        kind=ParameterKind.INPUT,
        absent_as="null",
        observed_values=("A000278094",),
    )
    with pytest.raises(InductionFailed, match="type or choose"):
        _refuse_an_unfillable_input(_version_asking_for(asked))

    _refuse_an_unfillable_input(_version_asking_for(with_options((asked,), planned)[0]))
