"""One press, several writes, and the value that flows between them.

**One logical create is often several physical resources.** Creating a client
on the real platform fires four POSTs behind a single Save -- addresses,
clients, clientWarehouse, packingConfigurations -- and the second carries an id
the first returned. `knowledge-base/KNOWLEDGE-BASE.md` 3b records it, and the
research capture holds the exchange: `POST /wm/clients` carries
`addressId: A000365896`, which no operator typed and `POST /wm/addresses`
answered with.

That is composition. Item 7 has been waiting for a chain between two mined jobs
and there is none -- 306 ordered pairs on the deployment, 0 -- but the same
shape, a value moving out of one write's answer and into the next write's body,
is what this platform does behind every cascade create. It is one press rather
than two jobs, and everything about the binding is the same.

**Nothing here is guessed.** A dependency is a value the SERVER made: in a
mutation's answer, not in its own request, and not typed by anybody earlier --
the same subtraction `uses_edges` makes between steps, made here between calls.
A form posting back what the operator typed is their value coming round again,
and an edit that PUTs a record it has just read carries the whole record back,
which is exactly what this must not read as a dependency.

**No instance in mined evidence yet, and that is the honest state.** Measured
2026-09-19 over three tenants' stores: four steps stand on a doing that wrote
twice, and not one of those second writes carries anything the first answered
with -- `Create a Supplier` PUTs an address that already existed. So this finds
nothing today, on purpose, and lights up the first time somebody creates a
client (or anything else with a cascade behind it) in front of the recorder.

`plan_step` reads it to refuse a replay it cannot send whole; the report reads
it to say what a press would really do.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.evidence import READ_METHODS
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import path_shape

K_SHORTEST = 3
"""How long a value must be before it can carry a dependency. `0`, `-1` and
`SG` are all over a warehouse body, and a flow drawn from one is a flow drawn
from a coincidence."""


@dataclass(frozen=True, slots=True)
class Flow:
    """One value, out of a write's answer and into the next write's body."""

    key: str
    """What the answer called it -- `addressId`."""

    into: str
    """What the later request calls it. Usually the same word, and never
    assumed to be: the flow is found by VALUE, and the two names are read off
    the two bodies."""

    made_at: str
    """The write that answered with it, as `METHOD path`."""

    used_at: str
    """The write that sent it on."""


def writes_of(doing: Gesture, ledger: Sequence[VerifiedWrite] = ()) -> list[Call]:
    """The calls of this doing that really write, in the order they went out.

    Only what the LEDGER recognises where one is given. A page fires
    keepalives, telemetry and performance beacons from the very click that
    creates a record -- `sessionKeepAlive` and `webPerformanceEntries/batch`
    are both in this store's evidence -- and counting those makes every real
    write look like a cascade.
    """
    return [
        call
        for call in doing.requests
        if call.method.upper() not in READ_METHODS
        and (not ledger or verified_write_for(call, tuple(ledger)) is not None)
    ]


def flows_in(doing: Gesture, typed: Mapping[str, float] | None = None) -> list[Flow]:
    """Every value this doing's own writes minted and its own later writes sent.

    `typed` is when each value was first typed or sent anywhere, which is what
    keeps an operator's own value from reading as the warehouse's. Optional,
    because a caller with one gesture in hand has nothing to compare against;
    then the subtraction is only against the minting call's own request, which
    is the narrower half of the same rule.
    """
    found: list[Flow] = []
    minted: list[tuple[str, str, str]] = []
    for call in writes_of(doing):
        where = f"{call.method.upper()} {path_shape(call.url)}"
        sent = _values(call.request_body.text if call.request_body is not None else None)
        for key, value, made_at in minted:
            into = [name for name, said in sent.items() if said == value]
            if into:
                found.append(Flow(key=key, into=into[0], made_at=made_at, used_at=where))
        if call.response_body is None:
            continue
        for key, value in _values(call.response_body.text).items():
            if value in sent.values():
                continue
            if typed is not None and (typed.get(value, float("inf")) <= doing.at):
                continue
            minted.append((key, value, where))
    return found


def _values(text: str | None) -> dict[str, str]:
    """A body's leaf strings, keyed, with the envelope read through.

    Blue Yonder answers a create with `{"@type": "ResponseBodyWrapper", "data":
    {…}}` -- 112 of the 114 successful writes in the research capture -- so a
    reader that stopped at the top level would find `@type` and nothing else.
    """
    if not text:
        return {}
    try:
        document = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(document, dict):
        return {}
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return {
        key: value.strip()
        for key, value in record.items()
        if isinstance(key, str) and isinstance(value, str) and len(value.strip()) >= K_SHORTEST
    }


__all__ = ["K_SHORTEST", "Flow", "flows_in", "writes_of"]
