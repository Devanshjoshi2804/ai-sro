"""What a demonstration looks like by the time a hosted model reads it.

Bodies had their credentials removed at capture, and the docstring here leaned
on that. URLs did not: a system that puts a session key or a one-time token in
a query string -- several do -- had it sent to Google in full, with the endpoint
it belonged to right beside it.

The URL itself stays. Which endpoint was called is the evidence; the query
string's values are not what the model is being asked about.
"""

from __future__ import annotations

from sro.application.induction.understand import _clean


def test_a_token_in_a_query_string_does_not_go() -> None:
    cleaned = _clean("https://wms.test/data/WM/wm/suppliers?access_token=abc123&siteId=SG")

    assert "abc123" not in cleaned
    assert "siteId=SG" in cleaned, "and the rest of the call is still readable"
    assert "/data/WM/wm/suppliers" in cleaned


def test_a_url_with_nothing_to_hide_is_untouched() -> None:
    plain = "https://wms.test/data/WM/wm/suppliers?siteId=SG"

    assert _clean(plain) == plain
