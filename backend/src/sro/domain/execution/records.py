"""What the warehouse called the record a call made.

Moved out of `application.execution.verify` unchanged, because two domain
modules now need it: `verify` reads it off a run's own reply, and
`what_it_writes` reads it off the evidence to decide whether a call made a
record at all. A domain module importing an application one is the wrong way
round, and copying the suffix rule into a second place is how two vocabularies
start drifting.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

K_IDENTIFIES = ("id", "code", "name", "number", "key")
"""Which fields of a create's answer say WHICH record it made.

Read by suffix and case-insensitively, because a warehouse names them its own
way: `equipmentTypeId`, `workAreaCode`, `supplierNumber`. Nothing else of the
body is kept -- a created record's answer is a row of somebody's data, and what
a person needs in order to go and look at it is what it is called."""

K_NAMED = 6
"""How many of those fields are kept. A record is identified by one or two of
them; a body with a dozen matching names is a list, not a record."""


K_CREATED = 201
"""What a record being MADE looks like on the wire, and the only answer this
names a record out of.

Measured on the deployment 2026-09-19, which is why it is here. `Create a
Customer Type` step 1 is "Navigate to the Customer Types screen": the page
POSTs the grid's query, the warehouse answers `200` with `{"name":
"customers"}` -- the collection's own name, metadata about a screen -- and
this read it as a record the run had made. Three of that tenant's runs carry
it, and `reversals.addresses` is happy with one field: the result card would
offer *Undo it*, and the press would aim a DELETE at "customers".

A 200 is not a create. An edit that answers with the record it changed made
nothing either, and a delete answers with an empty body and has nothing to
name. `reversals.K_CREATED` is the same number for the same reason, kept
separate because that one is about recognising a job and this is about
trusting an answer."""


def made_by(call: Mapping[str, object]) -> dict[str, str]:
    """What the warehouse called the record this create made.

    A run that made three records has to be able to say which three, or nobody
    can go and look at them -- and an undo, the day the evidence for one
    exists, has to address them by whatever the system called them.

    Never the whole body. A create's answer is a row of a customer's data, and
    this is stored on the run for as long as the tenant keeps it: what is kept
    is the handful of fields that NAME the row, and only where their values are
    short enough to be an identifier rather than a paragraph.
    """
    if call.get("status") != K_CREATED:
        # Nothing was made, so nothing is named. See `K_CREATED` above for the
        # navigation step whose grid query this used to read as a record.
        return {}
    text = call.get("body")
    return names_in(text if isinstance(text, str) else None)


def names_in(text: str | None) -> dict[str, str]:
    """The identifying fields of a body, whatever the answer's status was.

    `made_by` without its status rule, and the two are split because they
    answer different questions. This one asks "does this answer name a record
    at all", which is how `what_it_writes` tells a warehouse write from a
    page's own chatter -- Gmail's hundred POSTs name nothing, a supplier's
    address PUT names the address it edited. `made_by` asks the stronger
    question, "what did this call MAKE", and an edit makes nothing.
    """
    if not isinstance(text, str) or not text.strip():
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    # The envelope, before the record. Blue Yonder answers a create with
    # `{"@type": "ResponseBodyWrapper", "data": {…}}` -- 112 of the 114
    # successful writes in `knowledge-base/http/exchanges/*.jsonl`, and the live
    # deployment's own create of `GGD` is one of them. Read at the top level
    # that is `@type`, which names nothing, and `data`, which is a dict and
    # skipped: every real create would have said it made nothing at all.
    #
    # A `data` holding a LIST is left alone. That is `waves.jsonl`, the two
    # exceptions, and a list is not a record for the same reason `K_NAMED`
    # stops at a handful -- a body with a dozen identifying names is a
    # collection, and naming it as one row would be a lie on the run.
    inner = parsed.get("data")
    if isinstance(inner, dict):
        parsed = inner
    named: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str | int):
            continue
        if not key.lower().endswith(K_IDENTIFIES):
            continue
        said = str(value).strip()
        if said and len(said) <= 64:
            named[key] = said
        if len(named) == K_NAMED:
            break
    return named


__all__ = ["K_CREATED", "K_IDENTIFIES", "K_NAMED", "made_by"]
