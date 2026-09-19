"""A doing that wrote more than once is not one call to replay.

**One logical create is often several physical resources.** Creating a client
on the real platform fires four POSTs behind a single Save -- addresses,
clients, clientWarehouse, packingConfigurations -- each carrying an id the one
before it returned. `knowledge-base/KNOWLEDGE-BASE.md` 3b records it, watched
on the live host, with the warning in bold: never hand-construct a create from
one call.

The deterministic replay sends ONE call. The record it makes is the first of
four, the status says 201, the belts agree, and the run reports `held` over
half a client -- which is the worst shape a failure can have here, because
nothing about it looks like a failure.

Measured on this machine's store 2026-09-19, over every mined job of three
tenants: four steps stand on a doing that wrote twice. `new`'s `Create a
Supplier` step 13 is the cascade proper (`PUT /wm/addresses/{id}` then `POST
/wm/suppliers`); acme's `Create a Carrier Cross Reference` and `Create a Work
Operation` each POST twice into one collection, which is two records from one
press.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace

from sro.application.execution.plan_step import replay_without_asking
from sro.domain.execution.planning import Planned
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Body, Call, Gesture
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures

ORDERS = VerifiedWrite(method="POST", path_pattern="/api/orders")
ADDRESSES = VerifiedWrite(method="POST", path_pattern="/api/addresses")


def _saver(gesture_id: str = "doing-1", *extra: Call) -> Gesture:
    """The fixture's Save, with whatever else the page fired from that click."""
    one = copy.deepcopy(next(g for g in _gestures() if g.requests))
    one.id = gesture_id
    keep = next(r for r in one.requests if r.method == "POST" and "orders" in r.url)
    text = json.dumps({"clientCode": "ACME", "dock": "D3"})
    assert keep.request_body is not None
    one.requests = [replace(keep, request_body=replace(keep.request_body, text=text)), *extra]
    return one


def _call(method: str, url: str, status: int = 201) -> Call:
    said = json.dumps({"addressName": "one"})
    return Call(
        method=method,
        url=url,
        status=status,
        started_at=1.0,
        request_body=Body(text=said, size_bytes=len(said)),
    )


def _replay(*cited: Gesture, ledger: tuple[VerifiedWrite, ...] = (ORDERS,)) -> Planned | None:
    step = Step(order=0, says="save", system=None, cites=[one.id for one in cited])
    return replay_without_asking(
        step=step,
        cited=list(cited),
        values={},
        verified_writes=ledger,
    )


def test_one_write_behind_the_save_is_replayed() -> None:
    """The baseline this deployment runs live: one POST, one record, replayed
    deterministically. A refusal that fired here would put a model back in
    front of the one step that changes warehouse state."""
    planned = _replay(_saver())

    assert planned is not None and planned.kind == "http.send"


def test_a_save_that_wrote_twice_is_left_to_the_interface() -> None:
    """The cascade. Two ledger-recognised writes from one click, so replaying
    one of them makes half the record -- and the page, clicked, fires both in
    order with the ids it just received."""
    cascade = _saver("doing-1", _call("POST", "http://127.0.0.1:63319/api/addresses"))

    assert _replay(cascade, ledger=(ORDERS, ADDRESSES)) is None


def test_a_beacon_from_the_same_click_is_not_a_second_write() -> None:
    """A page fires keepalives, telemetry and performance beacons from the same
    press -- `sessionKeepAlive` and `webPerformanceEntries/batch` are both in
    this store's evidence. Counting those would refuse every real write on the
    platform, including the one that is proved live."""
    noisy = _saver("doing-1", _call("POST", "http://127.0.0.1:63319/api/sessionKeepAlive", 200))

    planned = _replay(noisy)

    assert planned is not None and planned.kind == "http.send"


def test_two_demonstrations_of_one_write_are_not_a_cascade() -> None:
    """Counted per DOING and never across the step's cites. A step cites one
    gesture per demonstration, so counting every cited call reads two doings of
    one write as a cascade -- which on this store refuses eight steps instead
    of four, including the live one."""
    planned = _replay(_saver("doing-1"), _saver("doing-2"))

    assert planned is not None and planned.kind == "http.send"
