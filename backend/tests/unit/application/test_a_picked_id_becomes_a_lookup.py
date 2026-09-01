from sro.application.induction.lookups import _listing_of, filtered_on
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
