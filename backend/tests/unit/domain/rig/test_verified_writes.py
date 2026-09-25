"""`verified_write_for` -- membership in the ledger, not resemblance to it."""

from sro.domain.execution.verified_writes import (
    VerifiedWrite,
    learned_pattern,
    verified_write_for,
)
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


# -- what a deployment learns for itself --------------------------------------
#
# `knowledge-base/index/write-endpoints.json` is a research project's file,
# edited by hand between sessions, and a deployment could not add to it. So a
# job whose write this system had watched succeed eight times -- each one
# confirmed by a read-back -- still clicked Save the ninth time. Measured on
# the deployment 2026-09-21: 26 steps planned from evidence against 162
# planned by a model.


def test_the_segment_this_run_typed_is_the_identifier() -> None:
    """Known, not guessed. The run typed GZ5 into Customer Type and the path
    ends `/customerTypes/GZ5`, so that segment is the id -- and `GZ5` is three
    characters with no digits, which no shape heuristic would ever star."""
    pattern = learned_pattern(
        "https://wms.example/data/WM/wm/customerTypes/GZ5?siteId=SG",
        {"Customer Type": "GZ5", "Description": "leaning new type"},
    )

    assert pattern == "/data/WM/wm/customerTypes/{id}"


def test_a_row_id_nobody_typed_is_still_an_identifier() -> None:
    """The second source, for ids no value names."""
    assert (
        learned_pattern("https://wms.example/data/WM/wm/addresses/1183", {})
        == "/data/WM/wm/addresses/{id}"
    )


def test_everything_else_stays_literal() -> None:
    """The ledger's own rule: never by assuming a documented-looking path
    behaves like a tested one. A pattern wider than the evidence is a licence
    to send a call nobody watched."""
    # A short value collides with route words. With `Department: wm` this
    # produced `/data/{id}/{id}/customerTypes`, which matches paths nobody has
    # ever watched. Only the last segment may be named by a value.
    assert (
        learned_pattern("https://wms.example/data/WM/wm/customerTypes", {"x": "wm"})
        == "/data/WM/wm/customerTypes"
    )
    assert (
        learned_pattern("https://wms.example/data/WM/wm/customerTypes/wm", {"x": "wm"})
        == "/data/WM/wm/customerTypes/{id}"
    ), "the identifier really is the last segment"
    assert (
        learned_pattern("https://wms.example/data/WM/wm/customerTypes", {})
        == "/data/WM/wm/customerTypes"
    )


def test_a_value_the_recording_held_differently_is_the_identifier_wherever_it_sits() -> None:
    assert (
        learned_pattern(
            "https://wms.example/api/customer-types/Acme%20Corp",
            {"Customer Type": "Acme Corp"},
            recorded="https://wms.example/api/customer-types/Beta%20Ltd",
        )
        == "/api/customer-types/{id}"
    )
    assert (
        learned_pattern(
            "https://wms.example/api/users/jane.doe@acme.com/roles",
            {"User": "jane.doe@acme.com"},
            recorded="https://wms.example/api/users/raj@acme.com/roles",
        )
        == "/api/users/{id}/roles"
    )


def test_a_segment_the_recording_holds_fixed_is_never_templated() -> None:
    assert (
        learned_pattern(
            "https://wms.example/orders/42/approve",
            {"Decision": "approve"},
            recorded="https://wms.example/orders/17/approve",
        )
        == "/orders/{id}/approve"
    )


def test_what_a_deployment_learnt_is_matched_the_same_way_the_file_is() -> None:
    """One vocabulary. The learned pattern goes through `verified_write_for`
    beside the file's entries, so a pattern that did not match the matcher
    would be a ledger entry that never fires."""
    learnt = VerifiedWrite(
        method="DELETE",
        path_pattern=learned_pattern(
            "https://wms.example/data/WM/wm/customerTypes/GZ5", {"Customer Type": "GZ5"}
        ),
    )

    found = verified_write_for(
        _call("DELETE", "https://wms.example/data/WM/wm/customerTypes/WDSL"), (learnt,)
    )

    assert found is learnt, "the next value was not covered by what was learnt"
