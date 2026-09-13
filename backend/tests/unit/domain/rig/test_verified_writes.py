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


def test_a_literal_dot_dot_segment_is_not_a_templated_match() -> None:
    """`_segments` splits the raw path on "/" before anything decodes it, so
    a literal `..` counts as one segment -- the same segment count as
    `{id}` -- and without the guard it is admitted as the address the
    server never actually walked to."""
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/..")

    assert verified_write_for(call, LEDGER) is None


def test_a_percent_encoded_dot_dot_segment_is_not_a_templated_match() -> None:
    """`%2e%2e` is one raw segment too, and decodes to the same `..` -- the
    guard has to decode before it judges, not just pattern-match the raw
    bytes."""
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/%2e%2e")

    assert verified_write_for(call, LEDGER) is None


def test_an_encoded_slash_smuggling_a_longer_path_is_not_a_templated_match() -> None:
    """`..%2f..%2fadmin%2fwipe` is one segment by an un-decoded split on "/",
    but Tomcat decodes `%2f` before it routes, so the segment this matcher
    would have called `{id}` and the path the server actually walks are two
    different things entirely."""
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/..%2f..%2fadmin%2fwipe")

    assert verified_write_for(call, LEDGER) is None


def test_a_segment_that_only_opens_a_brace_is_a_literal_and_not_a_wildcard() -> None:
    """Both ends, and `and` is what makes it both.

    A ledger typed as `{id` -- or a real path segment that happens to start
    with a brace -- would otherwise match ANY segment, which turns one
    mistyped entry into a licence to send a write to an endpoint nobody
    watched succeed. The module's own rule is membership, not resemblance.
    """
    ledger = (VerifiedWrite(method="PUT", path_pattern="/data/WM/wm/addresses/{id"),)
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/17")

    assert verified_write_for(call, ledger) is None


def test_a_templated_segment_matches_the_one_segment_it_stands_for() -> None:
    # The other half of the same `and`, so the pair cannot both be satisfied by
    # a matcher that ignores one end.
    call = _call("PUT", "https://wms.example/data/WM/wm/addresses/17")

    assert verified_write_for(call, LEDGER) is LEDGER[1]
