"""`verified_write_for` -- membership in the ledger, not resemblance to it."""

from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Call

LEDGER = (
    VerifiedWrite(method="post", path_pattern="/data/WM/wm/customerTypes"),
    VerifiedWrite(method="PUT", path_pattern="/data/WM/wm/addresses/{id}"),
)


def _call(method: str, url: str) -> Call:
    return Call(method=method, url=url)


def test_the_method_is_matched_without_regard_to_case() -> None:
    """`VerifiedWrite.__post_init__` upper-cases what it is given, so a ledger
    entry written lower-case still matches an upper-case call."""
    call = _call("POST", "https://wms.example/data/WM/wm/customerTypes")

    assert verified_write_for(call, LEDGER) is LEDGER[0]


def test_a_templated_segment_matches_any_single_path_segment() -> None:
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/addr-42")

    assert verified_write_for(call, LEDGER) is LEDGER[1]


def test_the_query_string_is_never_part_of_the_match() -> None:
    call = _call("POST", "https://wms.example/data/WM/wm/customerTypes?siteId=SG")

    assert verified_write_for(call, LEDGER) is LEDGER[0]


def test_an_extra_path_segment_is_not_a_match() -> None:
    """A templated segment stands for exactly one segment, not for the rest of
    the path -- `.../addresses/x/y` is not `.../addresses/{id}`."""
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/addr-42/history")

    assert verified_write_for(call, LEDGER) is None


def test_a_path_that_merely_resembles_a_verified_one_is_not_a_match() -> None:
    """The whole point of a ledger: a path a person has not individually
    watched succeed is not verified because it looks like one that has."""
    call = _call("POST", "https://wms.example/data/WM/wm/customerTypesArchive")

    assert verified_write_for(call, LEDGER) is None


def test_the_right_path_under_the_wrong_method_is_not_a_match() -> None:
    call = _call("DELETE", "https://wms.example/data/WM/wm/customerTypes")

    assert verified_write_for(call, LEDGER) is None


def test_an_empty_ledger_verifies_nothing() -> None:
    call = _call("POST", "https://wms.example/data/WM/wm/customerTypes")

    assert verified_write_for(call, ()) is None
