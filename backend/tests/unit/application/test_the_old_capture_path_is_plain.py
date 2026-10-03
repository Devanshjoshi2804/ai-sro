"""D-OLD: a control character in captured text must not reject a whole batch (jsonb refuses NUL),
and a gesture's frame path is as bounded as an effect's. Nothing else in today's batches moves."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sro.application.observation.redact import redact_events

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "observation"
    / "a_batch_that_carried_a_credential.ndjson"
)
# Measured before the change: the fixture carries no control character.
FIXTURE_MD5 = "6cb02a5ad0e294e9e5e8a4f15e0ae1e0"


def _gesture(**gesture: object) -> dict[str, object]:
    return {
        "kind": "gesture",
        "tab_id": 1,
        "gesture": {"kind": "click", "at": 1.0, "ref": "r.1", "url": "https://wms.example/a"}
        | gesture,
    }


def test_the_fixture_batch_is_byte_identical() -> None:
    events = [json.loads(x) for x in FIXTURE.read_text(encoding="utf-8").splitlines() if x]
    blob = b"".join(
        json.dumps(e, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
        for e in redact_events(events)
    )
    assert hashlib.md5(blob, usedforsecurity=False).hexdigest() == FIXTURE_MD5


def test_a_nul_in_an_outline_heading_no_longer_poisons_the_batch() -> None:
    outline = {"headings": ["Ship\x00ments​"], "fields": []}
    (out,) = redact_events([_gesture(outlines=[outline])])
    assert "\x00" not in json.dumps(out) and "\\u0000" not in json.dumps(out)
    assert out["gesture"]["outlines"][0]["headings"] == ["Shipments"]


def test_text_fields_keep_everything_but_control_characters() -> None:
    (out,) = redact_events([_gesture(value="a\x00b\r\nc")])
    assert out["gesture"]["value"] == "ab\r\nc"


def test_a_gestures_frame_path_is_capped_and_holds_index_and_url_only() -> None:
    hops = [{"index": i, "url": f"https://wms.example/{i}"} for i in range(40)]
    (out,) = redact_events([_gesture(frame_path=hops)])
    assert out["gesture"]["frame_path"] == hops[:16]
