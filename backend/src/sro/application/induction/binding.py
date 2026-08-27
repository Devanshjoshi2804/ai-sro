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

from sro.application.induction import jsonutil
from sro.application.induction.sites import parse_json
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame


def write_document(frame: ActionFrame) -> jsonutil.JsonValue | None:
    """The parsed body of the first non-background mutating request on `frame`.

    Shared with the diff: both need the call a gesture is *about*, not the
    reads and beacons that happened to land in the same frame.
    """
    write = next(
        (
            request
            for request in frame.requests
            if request.is_mutation and not is_background_traffic(request.url)
        ),
        None,
    )
    return parse_json(write.request_text) if write is not None else None


def key_filled_by(frame: ActionFrame, within: ActionFrame) -> str | None:
    """The pointer in `within`'s write that `frame`'s typed value filled."""
    typed = frame.action.value
    if not typed or frame.action.secret:
        return None

    document = write_document(within)
    if not isinstance(document, dict):
        return None

    wanted = _tidied(typed)
    found = [pointer for pointer, leaf in jsonutil.leaves(document) if _tidied(str(leaf)) == wanted]
    return found[0] if len(found) == 1 else None


def _tidied(value: str) -> str:
    return value.strip().casefold()
