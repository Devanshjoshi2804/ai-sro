"""What a batch holds, once the same call is counted once.

Ingest stores what arrived, verbatim and unedited, and that is right: what was
never stored cannot be recovered, and an operator's day is not repeatable the
way a demonstration is. So normalisation belongs here, on the way out -- where
every reader gets it, and where evidence already on disk is healed rather than
left wrong for as long as it is kept.

What is normalised is one browser defect. A relay injected into a frame a
second time forwarded the page realm's *same* record again, so one call arrived
as two adjacent, byte-identical lines carrying one `request_id`. The extension
no longer does it -- `network.js` refuses to relay where a live copy already is
-- but a day of recording was made while it did, and the miner whose whole job
is counting how often something happened counted every one of those twice.

The rule is narrow enough to be provable: a `request_id` is minted once per
call, by a counter in the realm that made the call. Two lines bearing one are
never two calls. Nothing else is touched -- a person really can click the same
control twice, and two identical gestures are two things they did.
"""

from __future__ import annotations

import json
from collections.abc import Mapping


def once_each(payload: bytes) -> bytes:
    """One upload's NDJSON with a repeated call's later copies dropped.

    Per payload, never across them: batches are already idempotent on the id
    the extension minted, and an id repeated in two batches is that idempotency
    to answer, not this.
    """
    seen: set[str] = set()
    kept: list[bytes] = []
    dropped = False
    for line in payload.splitlines():
        call = _request_id(line)
        if call is not None:
            if call in seen:
                dropped = True
                continue
            seen.add(call)
        kept.append(line)
    # The bytes themselves when there was nothing to do, which is every batch
    # an extension carrying the fix ever sends.
    return b"\n".join(kept) if dropped else payload


def _request_id(line: bytes) -> str | None:
    """The call this line reports, or ``None`` for a line that reports none.

    A line that will not decode is not a call anybody can identify, so it is
    kept and left to the reader that follows -- each of which already skips
    what it cannot read, and none of which should learn about it from here.
    """
    try:
        event = json.loads(line)
    except ValueError:
        return None
    if not isinstance(event, Mapping) or event.get("kind") != "request":
        return None
    request = event.get("request")
    if not isinstance(request, Mapping):
        return None
    call = request.get("request_id")
    return call if isinstance(call, str) and call else None
