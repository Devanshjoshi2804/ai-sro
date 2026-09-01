from sro.application.induction.lookups import Wanted, _listing_of, filtered_on, plan
from tests.unit.application.lookup_fixtures import a_frame, a_read, a_write


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
        "https://wms.example/addresses?query=[]",
        [{"addressId": "A1", "addressName": "also test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    pair_a = (a_frame(write),)
    # pair_b also carries a listing with the wanted value, positioned before its
    # own write -- exactly the shape `_first_mutation` would happily search. It
    # exists only to prove index 1 is bounded by `step_index` (0, excluding it)
    # rather than falling through to `other`'s rule.
    pair_b = (a_frame(listing_b), a_frame(write))
    other = (a_frame(listing), a_frame(write))

    # Both aligned doings (indices 0 and 1) are bounded by `step_index` -- one
    # holds only the write, the other holds a listing that bound must exclude.
    # `other`, at index 2, is outside the pair `_listing_of`'s `at < 2` test
    # distinguishes, so it is searched up to its own first mutation instead.
    found = _listing_of((pair_a, pair_b, other), value="A1", step_index=0)

    assert found is not None
    assert found[0].url == listing.url


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
        taken=set(),
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
            taken=set(),
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
            taken=set(),
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
            taken=set(),
        )
        == ()
    )


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
            taken=set(),
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
        taken=set(),
    )

    assert len(planned) == 1
    # `city` is sent by the write and unique in the one row the filter returned,
    # and shared by both addresses in the read that shows the collection.
    assert planned[0].options.label == ("addressName",)
