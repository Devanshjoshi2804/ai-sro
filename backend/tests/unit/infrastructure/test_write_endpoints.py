"""The write-safety ledger, read off disk -- and read gracefully when absent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sro.infrastructure.knowledge.write_endpoints import load_verified_writes

# Same guard as test_catalogue.py, same reason: a deployment without the
# knowledge base checked out beside it should skip this file's real-data
# assertions, not fail them.
ROOT = Path(__file__).resolve().parents[3].parent / "knowledge-base"


@pytest.mark.skipif(
    not (ROOT / "index" / "write-endpoints.json").is_file(),
    reason="the recorded knowledge base is not checked out here",
)
def test_the_real_ledger_verifies_the_two_mined_jobs_writes() -> None:
    load_verified_writes.cache_clear()
    verified = load_verified_writes(ROOT)

    patterns = {(v.method, v.path_pattern) for v in verified}
    assert ("POST", "/data/WM/wm/customerTypes") in patterns
    assert ("POST", "/data/WM/wm/equipmentTypes") in patterns


@pytest.mark.skipif(
    not (ROOT / "index" / "write-endpoints.json").is_file(),
    reason="the recorded knowledge base is not checked out here",
)
def test_the_real_ledgers_refusals_are_not_verified_whatever_the_flag_says() -> None:
    """Six entries are marked `verified: true` and were never watched succeed.

    Their own notes are unambiguous -- "422 already assigned to a load",
    "Cannot change inv_attr for inventory whose item is not inv_attr tracked",
    "Unable to delete order line because it is planned into a shipment". The
    route and the payload are confirmed; the success path is not. Handing one
    of these a live CSRF token is precisely what `verified_writes` exists to
    refuse, so the flag alone was never enough.
    """
    load_verified_writes.cache_clear()
    patterns = {(v.method, v.path_pattern) for v in load_verified_writes(ROOT)}

    assert ("POST", "/data/WM/wm/shipments/shipmentPlan") not in patterns
    assert ("POST", "/data/WM/wm/picks/confirm/async") not in patterns
    assert ("PUT", "/data/WM/wm/waves/cancelWave/async") not in patterns
    # And the tightening cost the ledger only those six.
    assert len(patterns) == 174


def test_an_entry_that_was_refused_is_not_verified(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {
                "method": "POST",
                "pathPattern": "/data/WM/wm/shipments/shipmentPlan",
                "verified": True,
                "proof": "refused",
            }
        ],
    )

    assert load_verified_writes(tmp_path) == ()


def test_an_entry_with_no_proof_at_all_is_not_verified(tmp_path: Path) -> None:
    """An allowlist and not a denylist of refusals: a `proof` this loader has
    never heard of -- a new vocabulary word, a typo, the field missing
    entirely -- is not a claim that anybody watched anything."""
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {"method": "POST", "pathPattern": "/data/WM/wm/a", "verified": True},
            {"method": "POST", "pathPattern": "/data/WM/wm/b", "verified": True, "proof": "hunch"},
        ],
    )

    assert load_verified_writes(tmp_path) == ()


def test_observed_once_is_enough_to_verify(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {
                "method": "DELETE",
                "pathPattern": "/data/WM/wm/packingConfigurations/{id}",
                "verified": True,
                "proof": "observed",
            }
        ],
    )

    assert len(load_verified_writes(tmp_path)) == 1


def test_a_missing_ledger_is_an_empty_one_not_an_error(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()

    assert load_verified_writes(tmp_path) == ()


def test_only_entries_marked_verified_are_kept(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {
                "method": "POST",
                "pathPattern": "/data/WM/wm/customerTypes",
                "verified": True,
                "proof": "round-trip",
            },
            {"method": "POST", "pathPattern": "/data/WM/wm/unproven", "verified": False},
        ],
    )

    verified = load_verified_writes(tmp_path)

    assert len(verified) == 1
    assert verified[0].path_pattern == "/data/WM/wm/customerTypes"


def test_a_duplicate_entry_is_kept_once(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {
                "method": "post",
                "pathPattern": "/data/WM/wm/customerTypes",
                "verified": True,
                "proof": "round-trip",
            },
            {
                "method": "POST",
                "pathPattern": "/data/WM/wm/customerTypes",
                "verified": True,
                "proof": "round-trip",
            },
        ],
    )

    verified = load_verified_writes(tmp_path)

    assert len(verified) == 1


def test_the_string_false_is_not_verified(tmp_path: Path) -> None:
    """`entry.get("verified")` used to be a truthiness test, and `"false"` is
    a non-empty string -- truthy in Python the same as in JavaScript, which
    is exactly the language a hand-edited JSON file gets typed against in
    someone's head. Only the real boolean `True` verifies an entry."""
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [{"method": "POST", "pathPattern": "/data/WM/wm/customerTypes", "verified": "false"}],
    )

    assert load_verified_writes(tmp_path) == ()


def test_an_empty_path_pattern_is_skipped_not_widened_into_the_site_root(tmp_path: Path) -> None:
    """An empty pattern splits into zero segments, which would otherwise
    match any zero-segment path -- the site root -- for every method. A
    malformed entry has to narrow the allowlist, never widen it."""
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [{"method": "POST", "pathPattern": "", "verified": True, "proof": "round-trip"}],
    )

    assert load_verified_writes(tmp_path) == ()


def test_a_path_pattern_missing_its_leading_slash_is_skipped(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [{"method": "POST", "pathPattern": "a/b", "verified": True, "proof": "round-trip"}],
    )

    assert load_verified_writes(tmp_path) == ()


def test_a_non_dict_entry_is_skipped_not_a_crash(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(tmp_path, ["not a dict", 42, None])  # type: ignore[list-item]

    assert load_verified_writes(tmp_path) == ()


def _write_ledger(root: Path, entries: list[dict]) -> None:
    index = root / "index"
    index.mkdir(parents=True, exist_ok=True)
    (index / "write-endpoints.json").write_text(json.dumps(entries))
