"""A flow claim only from the shape it can actually cite.

Synthetic fixtures, unlike test_catalogue.py -- this is about a shape the
recorded base's own corpus doesn't always use, not about what it currently
contains.
"""

from __future__ import annotations

import json
from pathlib import Path

from sro.domain.knowledge.entry import EntryKind
from sro.infrastructure.knowledge.catalogue import read_catalogue


def _write(root: Path, name: str, document: dict[str, object]) -> None:
    flows = root / "http" / "flows"
    flows.mkdir(parents=True, exist_ok=True)
    (flows / name).write_text(json.dumps(document))


def test_a_read_only_flat_shaped_flow_is_skipped_not_half_represented(tmp_path: Path) -> None:
    # No nested request/response at all -- method/url/status live top-level.
    _write(
        tmp_path,
        "readonly-receiving.json",
        {
            "screen": "receiving",
            "readOnly": True,
            "calls": [
                {
                    "seq": 0,
                    "method": "POST",
                    "url": "https://wms.test/api/sessionKeepAlive",
                    "status": 200,
                }
            ],
        },
    )

    claims = read_catalogue(tmp_path, system="blue_yonder")

    assert [claim for claim in claims if claim.kind is EntryKind.FLOW] == []


def test_a_full_cascade_flow_is_still_read_with_its_real_write_count(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "suppliers.json",
        {
            "spec": "suppliers",
            "resource": "suppliers",
            "applied": {"code": "ACME-2"},
            "calls": [
                {
                    "endpoint": "wm/suppliers",
                    "request": {"method": "POST", "url": "https://wms.test/api/suppliers"},
                    "response": {"status": 201},
                }
            ],
        },
    )

    claims = read_catalogue(tmp_path, system="blue_yonder")
    flows = [claim for claim in claims if claim.kind is EntryKind.FLOW]

    assert len(flows) == 1
    assert "1 writes" in flows[0].title
