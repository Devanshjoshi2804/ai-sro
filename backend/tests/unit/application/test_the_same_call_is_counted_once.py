"""A call relayed twice is one call.

The defect these guard against shipped in a browser extension and is fixed
there, but the recordings it made are kept for thirty days and are read by the
miner that decides what to offer an operator. See
`sro.application.observation.evidence`.
"""

from __future__ import annotations

import json

from sro.application.observation.evidence import once_each


def _call(request_id: str, url: str = "https://wms.example/api/orders") -> bytes:
    return json.dumps(
        {"kind": "request", "request": {"request_id": request_id, "method": "POST", "url": url}}
    ).encode()


def test_a_call_forwarded_twice_is_read_as_the_one_call_it_was() -> None:
    line = _call("req_1f2ff186_5")
    payload = b"\n".join([line, line])

    assert once_each(payload).splitlines() == [line]


def test_the_line_that_survives_is_the_one_that_arrived() -> None:
    """Byte-identical, not rebuilt: everything downstream reads fields off it
    that this module has no business knowing about."""
    line = _call("req_1f2ff186_5")

    assert once_each(b"\n".join([line, line])).splitlines()[0] == line


def test_two_different_calls_both_survive() -> None:
    first, second = _call("req_1f2ff186_5"), _call("req_1f2ff186_6")

    assert once_each(b"\n".join([first, second])).splitlines() == [first, second]


def test_the_same_gesture_twice_is_two_things_the_operator_did() -> None:
    """A person really can click the same control twice, and the count of how
    often they did is the whole signal this system runs on."""
    gesture = json.dumps({"kind": "gesture", "gesture": {"kind": "click", "at": 1.0}}).encode()

    assert len(once_each(b"\n".join([gesture, gesture])).splitlines()) == 2


def test_a_line_that_will_not_decode_is_left_for_its_reader() -> None:
    """Each reader already skips what it cannot parse, and each skips a
    different set. Deciding that here would quietly overrule all three."""
    payload = b"{not json at all\n" + _call("req_1f2ff186_5")

    assert len(once_each(payload).splitlines()) == 2


def test_a_batch_with_nothing_to_drop_is_returned_as_it_arrived() -> None:
    payload = b"\n".join([_call("req_1f2ff186_5"), _call("req_1f2ff186_6")])

    assert once_each(payload) is payload
