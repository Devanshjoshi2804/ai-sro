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


def test_a_missing_ledger_is_an_empty_one_not_an_error(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()

    assert load_verified_writes(tmp_path) == ()


def test_only_entries_marked_verified_are_kept(tmp_path: Path) -> None:
    load_verified_writes.cache_clear()
    _write_ledger(
        tmp_path,
        [
            {"method": "POST", "pathPattern": "/data/WM/wm/customerTypes", "verified": True},
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
            {"method": "post", "pathPattern": "/data/WM/wm/customerTypes", "verified": True},
            {"method": "POST", "pathPattern": "/data/WM/wm/customerTypes", "verified": True},
        ],
    )

    verified = load_verified_writes(tmp_path)

    assert len(verified) == 1


def _write_ledger(root: Path, entries: list[dict]) -> None:
    index = root / "index"
    index.mkdir(parents=True, exist_ok=True)
    (index / "write-endpoints.json").write_text(json.dumps(entries))
