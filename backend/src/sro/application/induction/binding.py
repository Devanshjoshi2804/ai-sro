"""Which field a keystroke filled.

A step can only be made conditional on a parameter if something proves the step
produces that parameter. The proof is already stored: what the operator typed
turns up in the write their next few gestures sent, under one key.

Normalised, because a form is allowed to tidy what it was given -- the work
area name uppercases as you type, a code field trims, a number field sends 1
for what was typed as "1". Nothing looser than that: a value that merely
contains another is not a match, and a value that fits two keys fits neither.
"""

from __future__ import annotations

from collections.abc import Iterator

from sro.application.induction import jsonutil
from sro.application.induction.sites import parse_json
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest


def _writes(frame: ActionFrame) -> Iterator[CapturedRequest]:
    """Every succeeded, non-background mutating call on this frame.

    A write the system rejected is not the write whose fields a step's typed
    values ended up in -- a failed, retried mutation must not stand in for the
    one that actually happened.
    """
    return (
        request
        for request in frame.requests
        if request.is_mutation and request.succeeded and not is_background_traffic(request.url)
    )


def write_document(frame: ActionFrame) -> jsonutil.JsonValue | None:
    """The parsed body of this frame's write, for a caller that already knows
    there is exactly one -- true once `explode` has split a gesture into
    per-step frames, which is where every caller but `key_filled_by` gets its
    frames from. `key_filled_by` runs earlier, when that is not yet true, and
    searches every write itself rather than assuming this one.
    """
    write = next(_writes(frame), None)
    return parse_json(write.request_text) if write is not None else None


def key_filled_by(frame: ActionFrame, within: ActionFrame) -> str | None:
    """The pointer in `within`'s write that `frame`'s typed value filled."""
    typed = frame.action.value
    if not typed or frame.action.secret:
        return None

    wanted = _tidied(typed)
    if not wanted:
        # A keystroke that typed nothing but whitespace is not evidence that
        # it filled anything -- without this, tidying would match it to every
        # field a form happened to send back empty.
        return None

    # This runs on frames as recorded, before `explode` splits a gesture's
    # several calls into separate steps -- a Save that creates a record and
    # then sets its address is one frame with two mutating writes, and there
    # is no principled "first" among them. So every write is searched, and
    # the ambiguity rule already applied within one body applies across
    # bodies too: a value that matches more than one write fits none of them.
    documents = [
        document
        for request in _writes(within)
        if isinstance(document := parse_json(request.request_text), dict)
    ]
    found = [
        pointer
        for document in documents
        for pointer, leaf in jsonutil.leaves(document)
        if _tidied(jsonutil.as_text(leaf)) == wanted
    ]
    return found[0] if len(found) == 1 else None


def _tidied(value: str) -> str:
    return value.strip().casefold()
