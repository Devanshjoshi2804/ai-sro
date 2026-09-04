"""The redaction rules, measured against the real capture, as a test.

Every measurement behind those rules used to be run by hand and then written
into a comment. That is how "the six new words match nothing" survived being
false: it was measured over 217 field names from one tenant subset and was
wrong at 3,254 names. It is also why `session` shipped for a round blanking
`sessionGroup`, `sessionNumber` and `sessionTag` -- a WMS session is a unit of
picking work, not a login -- and why nobody noticed until a research pass three
rounds later.

So the corpus is pinned here instead, and any change to a vocabulary, a
splitter or a shape pattern that moves a name or a value across the line fails
this file with the item named.

`corpus.json.gz` holds:

  names / headers   every distinct field, query-parameter and header name
  values            every distinct string value that carries no credential
  secret_*          what the rules answer for those names today
  withheld          values that DO carry a credential shape -- counted by
                    shape, never stored. Empty, and measured empty.

Drawn from the 296 files of `knowledge-base/http/exchanges` plus the acme rig
store: 83 gestures with their requests and page events, the orphan requests,
the orphan pages, and every `values_seen` an intent recorded. Blue Yonder WMS,
tenant acme, captured 2026-08. The store itself was a scratchpad and is gone;
this is what was taken out of it before it went.

The VALUES are the new half. Nothing had ever measured them -- only the names
-- and values are what the shape rule operates on.

To move a line here deliberately: run the rules over the fixture, read the
names this file prints, and put them in `secret_names` / `secret_headers`. That
edit is the human decision the test exists to demand.
"""

from __future__ import annotations

import gzip
import json
import pathlib
from typing import Any

from rig.wire import is_secret_header, is_secret_name, shapes_in

# Resolved from this file rather than from the working directory: the suite is
# copied wholesale into `mutants/` by a mutation run, and a repo-relative path
# resolves to nothing from in there.
CORPUS_FILE = pathlib.Path(__file__).parent / "corpus.json.gz"


def _corpus() -> dict[str, Any]:
    with gzip.open(CORPUS_FILE, "rt", encoding="utf-8") as fh:
        loaded: dict[str, Any] = json.load(fh)
    return loaded


CORPUS = _corpus()


def test_the_fixture_is_the_whole_corpus() -> None:
    """A truncated fixture would pass every assertion below by having nothing
    left to disagree about."""
    assert CORPUS["counts"] == {"names": 3227, "headers": 29, "values": 47969}
    assert len(CORPUS["names"]) == 3227
    assert len(CORPUS["headers"]) == 29
    assert len(CORPUS["values"]) == 47969


def test_which_real_field_names_the_word_rule_calls_credentials() -> None:
    """Eight of 3,227, and three of them are false positives that were kept
    knowingly: `onePassOnly` and `passAssignmentUnassignWork` are picking
    operations -- a "pass" in this domain -- and `verificationCode` is a WMS
    check digit. The bare word `pass` costs those two and buys `db_pass`,
    `user_pass`, `adminPass` and a plain `?pass=`; that trade is written up in
    sensitivity.py. This test is what makes the next such trade visible on the
    commit that makes it."""
    flagged = sorted(name for name in CORPUS["names"] if is_secret_name(name))
    expected = sorted(CORPUS["secret_names"])

    assert flagged == expected, (
        f"newly blanked: {sorted(set(flagged) - set(expected))}\n"
        f"no longer blanked: {sorted(set(expected) - set(flagged))}"
    )


def test_which_real_header_names_the_header_rule_calls_credentials() -> None:
    """Four of 29, and the header rule matches on substrings where the field
    rule matches on whole words -- so this is the more dangerous of the two.
    `authenticated: "true"` is a boolean that becomes a vault reference, and
    `X-Requested-With: XMLHttpRequest` is a constant; both were accepted
    deliberately."""
    flagged = sorted(name for name in CORPUS["headers"] if is_secret_header(name))
    expected = sorted(CORPUS["secret_headers"])

    assert flagged == expected, (
        f"newly blanked: {sorted(set(flagged) - set(expected))}\n"
        f"no longer blanked: {sorted(set(expected) - set(flagged))}"
    )


def test_no_real_value_in_this_corpus_looks_like_a_credential() -> None:
    """The measurement that had never been made, and the one that says the
    shape rule is free: zero of 47,969 real values match any of the nine
    patterns. A pattern that starts matching one is not automatically wrong --
    a JWT genuinely present in captured WMS traffic is a finding in its own
    right -- but it is a human's call, not a silent widening."""
    flagged = {value: shapes_in(value) for value in CORPUS["values"] if shapes_in(value)}

    assert not flagged, "\n".join(
        f"{shapes} now matches a real value: {value[:120]!r}" for value, shapes in flagged.items()
    )


def test_the_fixture_carries_no_credential_of_its_own() -> None:
    """The corpus is real customer traffic, so the rule for building this
    fixture is that a value carrying a credential shape is recorded as its
    classification and never as itself. `withheld` counts them by shape. It is
    empty because nothing in the capture matched -- if a rebuild ever fills it,
    the count is the finding and the value still does not come into the repo."""
    assert CORPUS["withheld"] == {}
